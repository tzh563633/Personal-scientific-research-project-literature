from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Job, Paper, PaperFile, User, now
from ..schemas import JobResponse, PaperFileResponse, PaperPatch, PaperResponse
from ..services.files import (
    ALLOWED_PAPER_EXTENSIONS,
    file_metadata,
    guess_mime,
    relative_storage_path,
    save_upload,
)
from ..worker import enqueue_paper

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/upload", response_model=JobResponse)
async def upload_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        path, sha256, size = await save_upload(file, "uploads", ALLOWED_PAPER_EXTENSIONS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    duplicate_file = db.query(PaperFile).filter(PaperFile.sha256 == sha256).first()
    if duplicate_file:
        path.unlink(missing_ok=True)
        job = Job(
            kind="paper_processing",
            entity_id=duplicate_file.paper_id,
            status="succeeded",
            progress=100,
            message="Duplicate file skipped",
            result={"paper_id": duplicate_file.paper_id, "duplicate": True},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    metadata = file_metadata(file.filename or "untitled", file.content_type)
    title = Path(metadata["original_name"]).stem
    paper = Paper(title=title, file_path=relative_storage_path(path), status="pending")
    db.add(paper)
    db.flush()
    db.add(
        PaperFile(
            paper_id=paper.id,
            kind="original",
            path=relative_storage_path(path),
            sha256=sha256,
            size_bytes=size,
            original_name=metadata["original_name"],
            extension=metadata["extension"],
            mime_type=metadata["mime_type"],
        )
    )
    job = Job(kind="paper_processing", entity_id=paper.id, status="pending", message="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_paper(db, job.id)
    db.refresh(job)
    return job


@router.post("/upload/batch", response_model=list[JobResponse])
async def upload_papers_batch(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not files or len(files) > 50:
        raise HTTPException(status_code=400, detail="Batch upload supports 1 to 50 files")
    jobs = []
    for file in files:
        jobs.append(await upload_paper(file=file, db=db, _=user))
    return jobs


@router.get("", response_model=list[PaperResponse])
def list_papers(
    query: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    statement = db.query(Paper).order_by(Paper.updated_at.desc())
    if query:
        statement = statement.filter(Paper.title.ilike(f"%{query}%"))
    if status:
        statement = statement.filter(Paper.status == status)
    return statement.limit(200).all()


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.patch("/{paper_id}", response_model=PaperResponse)
def patch_paper(
    paper_id: int,
    payload: PaperPatch,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)
    paper.updated_at = now()
    db.commit()
    db.refresh(paper)
    return paper


@router.get("/{paper_id}/files", response_model=list[PaperFileResponse])
def list_paper_files(paper_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Paper, paper_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return db.query(PaperFile).filter(PaperFile.paper_id == paper_id).all()


@router.get("/{paper_id}/files/{file_id}")
def download_paper_file(
    paper_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    paper_file = (
        db.query(PaperFile)
        .filter(PaperFile.paper_id == paper_id, PaperFile.id == file_id)
        .first()
    )
    if not paper_file:
        raise HTTPException(status_code=404, detail="File not found")
    from ..services.files import absolute_storage_path

    path = absolute_storage_path(paper_file.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File is missing from storage")
    return FileResponse(path, filename=path.name)

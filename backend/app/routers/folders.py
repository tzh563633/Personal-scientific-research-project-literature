from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import AgentJob, FolderDocument, Job, PaperFolder, User, now
from ..schemas import FolderCreate, FolderDocumentResponse, FolderResponse, FolderScanRequest, JobResponse, OkResponse
from ..services.folders import validate_host_folder_path

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=list[FolderResponse])
def list_folders(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(PaperFolder).order_by(PaperFolder.name).limit(100).all()


@router.post("", response_model=FolderResponse)
def create_folder(
    payload: FolderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        path = validate_host_folder_path(payload.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    folder = PaperFolder(
        name=payload.name.strip(),
        path=path,
        recursive=payload.recursive,
        enabled=payload.enabled,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.put("/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: int,
    payload: FolderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    folder = db.get(PaperFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    try:
        folder.path = validate_host_folder_path(payload.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    folder.name = payload.name.strip()
    folder.recursive = payload.recursive
    folder.enabled = payload.enabled
    folder.updated_at = now()
    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/{folder_id}", response_model=OkResponse)
def delete_folder(folder_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    folder = db.get(PaperFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    db.delete(folder)
    db.commit()
    return OkResponse()


@router.get("/{folder_id}/documents", response_model=list[FolderDocumentResponse])
def list_folder_documents(
    folder_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not db.get(PaperFolder, folder_id):
        raise HTTPException(status_code=404, detail="Folder not found")
    statement = db.query(FolderDocument).filter(FolderDocument.folder_id == folder_id)
    if status:
        statement = statement.filter(FolderDocument.import_status == status)
    return statement.order_by(FolderDocument.updated_at.desc()).limit(2000).all()


@router.post("/{folder_id}/scan", response_model=JobResponse)
def scan_folder(
    folder_id: int,
    payload: FolderScanRequest | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    folder = db.get(PaperFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    if not folder.enabled:
        raise HTTPException(status_code=400, detail="Folder is disabled")
    limits = payload or FolderScanRequest()
    job = Job(kind="folder_scan", entity_id=folder.id, status="pending", message="Waiting for host Agent")
    db.add(job)
    db.flush()
    db.add(
        AgentJob(
            job_id=job.id,
            kind="scan_folder",
            payload={
                "folder_id": folder.id,
                "path": folder.path,
                "recursive": folder.recursive,
                "max_files": limits.max_files,
            },
            status="pending",
        )
    )
    folder.last_scan_job_id = job.id
    folder.updated_at = now()
    db.commit()
    db.refresh(job)
    return job

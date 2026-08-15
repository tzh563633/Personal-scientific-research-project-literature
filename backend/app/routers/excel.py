from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..dependencies import get_current_user
from ..models import ExcelUpdate, Job, User
from ..schemas import ExcelUpdateResponse, JobResponse
from ..services.excel import EXCEL_PATH, generate_excel
from ..worker import enqueue_job

router = APIRouter(prefix="/excel", tags=["excel"])


@router.get("/download")
def download_excel(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not EXCEL_PATH.exists():
        generate_excel(db)
    return FileResponse(EXCEL_PATH, filename="papers.xlsx")


@router.post("/update", response_model=JobResponse)
def update_excel(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = Job(kind="excel_update", status="pending", message="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_job(db, job.id, "excel_update")
    db.refresh(job)
    return job


@router.get("/updates", response_model=list[ExcelUpdateResponse])
def list_excel_updates(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ExcelUpdate).order_by(ExcelUpdate.created_at.desc()).limit(100).all()

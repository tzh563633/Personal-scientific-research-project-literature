from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Job, User
from ..schemas import JobResponse
from ..worker import enqueue_job

router = APIRouter(prefix="/monitor", tags=["journals"])


@router.post("/run", response_model=JobResponse)
def run_monitor(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = Job(kind="journal_monitor", status="pending", message="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_job(db, job.id, "journal_monitor")
    db.refresh(job)
    return job

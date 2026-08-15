from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Alert, Journal, Job, Keyword, User
from ..schemas import (
    AlertResponse,
    JournalCreate,
    JournalResponse,
    KeywordCreate,
    KeywordResponse,
    JobResponse,
    OkResponse,
)
from ..services.journals import monitor_journals
from ..schemas import JobResponse
from ..worker import enqueue_job

router = APIRouter(prefix="/journals", tags=["journals"])


@router.get("", response_model=list[JournalResponse])
def list_journals(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Journal).order_by(Journal.name).all()


@router.post("", response_model=JournalResponse)
def create_journal(
    payload: JournalCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    journal = Journal(**payload.model_dump())
    db.add(journal)
    db.commit()
    db.refresh(journal)
    return journal


@router.put("/{journal_id}", response_model=JournalResponse)
def update_journal(
    journal_id: int,
    payload: JournalCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    for key, value in payload.model_dump().items():
        setattr(journal, key, value)
    db.commit()
    db.refresh(journal)
    return journal


@router.delete("/{journal_id}", response_model=OkResponse)
def delete_journal(journal_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    journal = db.get(Journal, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    db.delete(journal)
    db.commit()
    return OkResponse()


@router.get("/{journal_id}/keywords", response_model=list[KeywordResponse])
def list_keywords(journal_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")
    return db.query(Keyword).filter(Keyword.journal_id == journal_id).order_by(Keyword.keyword).all()


@router.post("/{journal_id}/keywords", response_model=KeywordResponse)
def create_keyword(
    journal_id: int,
    payload: KeywordCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not db.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="Journal not found")
    keyword = Keyword(journal_id=journal_id, **payload.model_dump())
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


@router.delete("/{journal_id}/keywords/{keyword_id}", response_model=OkResponse)
def delete_keyword(
    journal_id: int,
    keyword_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    keyword = (
        db.query(Keyword)
        .filter(Keyword.id == keyword_id, Keyword.journal_id == journal_id)
        .first()
    )
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(keyword)
    db.commit()
    return OkResponse()


@router.post("/monitor/run", response_model=JobResponse)
def run_monitor(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = Job(kind="journal_monitor", status="pending", message="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_job(db, job.id, "journal_monitor")
    db.refresh(job)
    return job


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Alert).order_by(Alert.created_at.desc()).limit(100).all()

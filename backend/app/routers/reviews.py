from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Job, ReviewFramework, ReviewOutput, ReviewSource, User
from ..schemas import (
    FrameworkCreate,
    FrameworkResponse,
    ReviewGenerateRequest,
    ReviewOutputResponse,
    ReviewSourceResponse,
    JobResponse,
)
from ..worker import enqueue_job

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/frameworks", response_model=FrameworkResponse)
def create_framework(
    payload: FrameworkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    framework = ReviewFramework(**payload.model_dump())
    db.add(framework)
    db.commit()
    db.refresh(framework)
    return framework


@router.get("/frameworks", response_model=list[FrameworkResponse])
def list_frameworks(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ReviewFramework).order_by(ReviewFramework.created_at.desc()).all()


@router.post("/generate", response_model=JobResponse)
def generate(
    payload: ReviewGenerateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    framework = db.get(ReviewFramework, payload.framework_id)
    if not framework:
        raise HTTPException(status_code=404, detail="Framework not found")
    if payload.excel_path is not None:
        framework.excel_path = payload.excel_path
        db.commit()
        db.refresh(framework)
    job = Job(kind="review_generation", entity_id=framework.id, status="pending", message="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    if payload.deepseek_api_key:
        from ..services.reviews import generate_review
        from ..models import now

        job.status = "running"
        job.started_at = now()
        job.progress = 10
        db.commit()
        try:
            output = generate_review(
                db,
                framework,
                transient_deepseek_api_key=payload.deepseek_api_key,
            )
            job.progress = 100
            job.status = "succeeded"
            job.result = {"review_output_id": output.id}
            job.finished_at = now()
            job.message = "Review generated"
            db.commit()
        except Exception as exc:
            db.rollback()
            job = db.get(Job, job.id)
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = now()
            db.commit()
    else:
        enqueue_job(db, job.id, "review_generation")
    db.refresh(job)
    return job


@router.get("/outputs", response_model=list[ReviewOutputResponse])
def list_outputs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ReviewOutput).order_by(ReviewOutput.created_at.desc()).limit(100).all()


@router.get("/outputs/{output_id}/sources", response_model=list[ReviewSourceResponse])
def list_output_sources(
    output_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not db.get(ReviewOutput, output_id):
        raise HTTPException(status_code=404, detail="Review output not found")
    return (
        db.query(ReviewSource)
        .filter(ReviewSource.output_id == output_id)
        .order_by(ReviewSource.id)
        .all()
    )

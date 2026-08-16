from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Agent, Alert, CodeProject, ExcelUpdate, Job, Journal, Paper, ReviewOutput, User
from ..schemas import DashboardOverviewResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    recent_papers = db.query(Paper).order_by(Paper.updated_at.desc()).limit(5).all()
    recent_alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(5).all()
    recent_reviews = db.query(ReviewOutput).order_by(ReviewOutput.created_at.desc()).limit(5).all()
    latest_excel_update = db.query(ExcelUpdate).order_by(ExcelUpdate.update_time.desc()).first()

    return DashboardOverviewResponse(
        generated_at=datetime.utcnow(),
        paper_count=db.query(func.count(Paper.id)).scalar() or 0,
        processed_paper_count=db.query(func.count(Paper.id)).filter(Paper.status == "processed").scalar() or 0,
        pending_paper_count=db.query(func.count(Paper.id)).filter(Paper.status != "processed").scalar() or 0,
        journal_count=db.query(func.count(Journal.id)).scalar() or 0,
        enabled_journal_count=db.query(func.count(Journal.id)).filter(Journal.enabled.is_(True)).scalar() or 0,
        alert_count=db.query(func.count(Alert.id)).scalar() or 0,
        review_output_count=db.query(func.count(ReviewOutput.id)).scalar() or 0,
        code_project_count=db.query(func.count(CodeProject.id)).scalar() or 0,
        online_agent_count=db.query(func.count(Agent.id)).filter(Agent.status == "online").scalar() or 0,
        active_job_count=db.query(func.count(Job.id)).filter(Job.status.in_(("pending", "running"))).scalar() or 0,
        latest_excel_update=latest_excel_update,
        recent_papers=recent_papers,
        recent_alerts=recent_alerts,
        recent_reviews=recent_reviews,
    )

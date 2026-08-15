from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import AgentJob, Command, User, now
from ..schemas import CommandCreate, CommandResponse

router = APIRouter(prefix="/commands", tags=["commands"])


def parse_intent(text: str) -> str | None:
    lowered = text.lower()
    if any(term in lowered for term in ("excel", "表格", "汇总")):
        return "update_excel"
    if any(term in lowered for term in ("期刊", "监控", "journal", "monitor", "rss")):
        return "monitor_journals"
    if any(term in lowered for term in ("综述", "review")):
        return "generate_review"
    if any(term in lowered for term in ("备份", "backup")):
        return "backup"
    return None


@router.post("", response_model=CommandResponse)
def create_command(
    payload: CommandCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    intent = parse_intent(payload.text)
    command = Command(text=payload.text, intent=intent, status="pending" if intent else "failed")
    db.add(command)
    db.commit()
    db.refresh(command)
    if not intent:
        command.error = "Command is outside the business allowlist"
        db.commit()
        return command
    job = AgentJob(command_id=command.id, kind=intent, payload={})
    db.add(job)
    db.flush()
    command.result = {"agent_job_id": job.id}
    db.commit()
    db.refresh(command)
    return command


@router.get("", response_model=list[CommandResponse])
def list_commands(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Command).order_by(Command.created_at.desc()).limit(100).all()


@router.get("/{command_id}", response_model=CommandResponse)
def get_command(command_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    command = db.get(Command, command_id)
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    return command

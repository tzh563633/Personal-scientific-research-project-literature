from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models import Agent, AgentJob, Command, Job, PaperFolder, now
from ..schemas import (
    AgentFolderDocumentResponse,
    AgentClaimRequest,
    AgentClaimResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentHeartbeatRequest,
    AgentJobResponse,
    AgentRegisterRequest,
    AgentRegisterResponse,
    AgentResultRequest,
    OkResponse,
)
from ..services.backup import create_backup
from ..services.excel import generate_excel
from ..services.journals import monitor_journals
from ..services.reviews import generate_review

router = APIRouter(prefix="/agent", tags=["agent"])


def check_token(token: str | None) -> None:
    if not token or token != settings.agent_token:
        raise HTTPException(status_code=401, detail="Invalid agent token")


@router.post("/register", response_model=AgentRegisterResponse)
def register(
    payload: AgentRegisterRequest | None = None,
    x_agent_token: str | None = Header(default=None),
):
    check_token(x_agent_token)
    payload = payload or AgentRegisterRequest(
        capabilities=["backup", "update_excel", "monitor_journals", "generate_review", "scan_folder"]
    )
    db: Session = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.name == payload.name).first()
        if not agent:
            agent = Agent(name=payload.name)
            db.add(agent)
        agent.status = "online"
        agent.capabilities = payload.capabilities
        agent.last_seen_at = now()
        agent.updated_at = now()
        db.commit()
        db.refresh(agent)
        return AgentRegisterResponse(
            ok=True,
            agent_id=agent.id,
            capabilities=agent.capabilities or [],
        )
    finally:
        db.close()


@router.post("/folders/{folder_id}/documents", response_model=AgentFolderDocumentResponse)
async def upload_folder_document(
    folder_id: int,
    file: UploadFile = File(...),
    relative_path: str = Form(...),
    sha256: str | None = Form(default=None),
    modified_at: str | None = Form(default=None),
    x_agent_token: str | None = Header(default=None),
):
    check_token(x_agent_token)
    db: Session = SessionLocal()
    try:
        folder = db.get(PaperFolder, folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        if not folder.enabled:
            raise HTTPException(status_code=400, detail="Folder is disabled")
        from ..services.folders import ingest_agent_document

        document, duplicate = await ingest_agent_document(
            db,
            folder,
            file,
            relative_path=relative_path,
            submitted_sha256=sha256,
            modified_at=modified_at,
        )
        return AgentFolderDocumentResponse(document=document, duplicate=duplicate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()


@router.post("/heartbeat", response_model=OkResponse)
def heartbeat(
    payload: AgentHeartbeatRequest,
    x_agent_token: str | None = Header(default=None),
):
    check_token(x_agent_token)
    db: Session = SessionLocal()
    try:
        agent = db.get(Agent, payload.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        agent.status = "online"
        agent.last_seen_at = now()
        agent.updated_at = now()
        db.commit()
        return OkResponse()
    finally:
        db.close()


@router.post("/execute", response_model=AgentExecuteResponse)
def execute(
    payload: AgentExecuteRequest,
    x_agent_token: str | None = Header(default=None),
):
    check_token(x_agent_token)
    db: Session = SessionLocal()
    try:
        kind = payload.kind
        if kind == "backup":
            return AgentExecuteResponse(ok=True, path=str(create_backup()))
        if kind == "update_excel":
            return AgentExecuteResponse(ok=True, update_id=generate_excel(db).id)
        if kind == "monitor_journals":
            return AgentExecuteResponse(ok=True, result=monitor_journals(db))
        if kind == "generate_review":
            from ..models import ReviewFramework

            framework = db.query(ReviewFramework).order_by(ReviewFramework.id.desc()).first()
            if not framework:
                return AgentExecuteResponse(ok=False, error="No review framework exists")
            return AgentExecuteResponse(ok=True, output_id=generate_review(db, framework).id)
        return AgentExecuteResponse(ok=False, error=f"Unsupported agent job: {kind}")
    except Exception as exc:
        return AgentExecuteResponse(ok=False, error=str(exc))
    finally:
        db.close()


@router.post("/jobs/claim", response_model=AgentClaimResponse)
def claim_job(
    payload: AgentClaimRequest,
    x_agent_token: str | None = Header(default=None),
):
    check_token(x_agent_token)
    db: Session = SessionLocal()
    try:
        agent = db.get(Agent, payload.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        job = (
            db.query(AgentJob)
            .filter(AgentJob.status == "pending")
            .order_by(AgentJob.created_at)
            .with_for_update(skip_locked=True)
            .first()
        )
        if not job:
            return AgentClaimResponse(job=None)
        job.status = "running"
        job.agent_id = agent.id
        job.claimed_at = now()
        agent.status = "busy"
        agent.last_seen_at = now()
        db.commit()
        return AgentClaimResponse(
            job=AgentJobResponse(id=job.id, kind=job.kind, payload=job.payload)
        )
    finally:
        db.close()


@router.post("/jobs/{job_id}/result", response_model=OkResponse)
def result(
    job_id: int,
    payload: AgentResultRequest,
    x_agent_token: str | None = Header(default=None),
):
    check_token(x_agent_token)
    db: Session = SessionLocal()
    try:
        job = db.get(AgentJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Agent job not found")
        job.status = "succeeded" if payload.ok else "failed"
        job.result = payload.model_dump(exclude_none=True)
        job.error = payload.error
        if job.job_id:
            platform_job = db.get(Job, job.job_id)
            if platform_job:
                platform_job.status = "succeeded" if payload.ok else "failed"
                platform_job.progress = 100 if payload.ok else platform_job.progress
                platform_job.result = payload.result or {}
                platform_job.error = payload.error
                platform_job.message = "Folder scan completed" if payload.ok else "Folder scan failed"
                platform_job.finished_at = now()
                folder_id = platform_job.entity_id
                if folder_id:
                    folder = db.get(PaperFolder, folder_id)
                    if folder:
                        folder.last_scan_at = now()
                        folder.updated_at = now()
        if job.command_id:
            command = db.get(Command, job.command_id)
            if command:
                command.status = job.status
                command.result = payload.model_dump(exclude_none=True)
                command.error = job.error
                command.finished_at = now()
        if job.agent_id:
            agent = db.get(Agent, job.agent_id)
            if agent:
                agent.status = "online"
                agent.last_seen_at = now()
        db.commit()
        return OkResponse()
    finally:
        db.close()

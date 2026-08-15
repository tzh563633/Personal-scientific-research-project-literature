from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..dependencies import get_admin_user
from ..models import AcademicSource, AuditLog, SystemConfig, User
from ..schemas import AcademicSourceCreate, AcademicSourceResponse, ConfigResponse, ConfigUpdate
from ..schemas import OkResponse
from ..services.crypto import encrypt_secret

router = APIRouter(prefix="/system", tags=["system"])
SECRET_KEYS = {
    "DEEPSEEK_API_KEY",
    "QWEN_API_KEY",
    "KIMI_API_KEY",
    "SMTP_PASSWORD",
    "SMTP_USER",
    "AGENT_TOKEN",
}


@router.get("/config", response_model=ConfigResponse)
def get_config(db: Session = Depends(get_db), _: User = Depends(get_admin_user)):
    values = {
        "DEFAULT_LLM": settings.default_llm,
        "OCR_ENABLED": settings.ocr_enabled,
        "MAX_UPLOAD_BYTES": settings.max_upload_bytes,
        "SMTP_HOST": settings.smtp_host,
        "SMTP_PORT": settings.smtp_port,
    }
    for item in db.query(SystemConfig).all():
        values[item.key] = "***" if item.is_secret and item.value else item.value
    return ConfigResponse(values)


@router.put("/config", response_model=OkResponse)
def update_config(
    payload: ConfigUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    for key, value in payload.values.items():
        item = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if not item:
            item = SystemConfig(key=key, is_secret=key.upper() in SECRET_KEYS)
            db.add(item)
        if not (item.is_secret and value == "***"):
            raw_value = None if value is None else str(value)
            item.value = encrypt_secret(raw_value) if item.is_secret and raw_value is not None else raw_value
    db.add(AuditLog(action="system.config.update", detail={"keys": list(payload.values)}))
    db.commit()
    return OkResponse()


@router.post("/academic-source", response_model=AcademicSourceResponse)
def add_academic_source(
    payload: AcademicSourceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    import json

    encrypted = encrypt_secret(json.dumps(payload.config, ensure_ascii=False))
    source = AcademicSource(source_name=payload.source_name, encrypted_config=encrypted)
    db.add(source)
    db.commit()
    db.refresh(source)
    return AcademicSourceResponse(
        id=source.id,
        source_name=source.source_name,
        enabled=source.enabled,
    )


@router.get("/logs", response_model=list[str])
def get_logs(_: User = Depends(get_admin_user)):
    log_path = Path(settings.storage_path) / "logs" / "app.log"
    if not log_path.exists():
        return []
    return log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:]

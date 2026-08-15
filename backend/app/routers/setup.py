from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SystemConfig, User
from ..schemas import SetupAdminRequest, SetupAdminResponse, SetupStatus
from ..security import hash_password

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatus)
def status(db: Session = Depends(get_db)):
    return SetupStatus(initialized=db.query(User).count() > 0)


@router.post("/admin", response_model=SetupAdminResponse)
def create_admin(payload: SetupAdminRequest, db: Session = Depends(get_db)):
    if db.query(User).count():
        raise HTTPException(status_code=409, detail="System is already initialized")
    try:
        db.add(SystemConfig(key="setup.completed", value="true", is_secret=False))
        db.flush()
        user = User(username=payload.username, password_hash=hash_password(payload.password), role="admin")
        db.add(user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="System is already initialized") from exc
    return SetupAdminResponse()

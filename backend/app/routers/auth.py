from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import bearer, get_current_user
from ..models import RevokedToken, User
from ..schemas import LoginRequest, LogoutResponse, TokenResponse
from ..security import create_access_token, token_expiry, token_hash, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.username))


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    existing = db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash(credentials.credentials)).first()
    if not existing:
        db.add(
            RevokedToken(
                token_hash=token_hash(credentials.credentials),
                expires_at=token_expiry(credentials.credentials),
            )
        )
        db.commit()
    return LogoutResponse()

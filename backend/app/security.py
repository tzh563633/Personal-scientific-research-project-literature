import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings


def _bcrypt_input(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_input(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_input(password), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": subject, "exp": expires}, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    subject = payload.get("sub")
    if not subject:
        raise ValueError("Token subject is missing")
    return str(subject)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_expiry(token: str) -> datetime:
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    expiry = payload.get("exp")
    if not expiry:
        raise ValueError("Token expiry is missing")
    return datetime.fromtimestamp(float(expiry), tz=timezone.utc).replace(tzinfo=None)

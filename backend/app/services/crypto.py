from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from ..config import settings


def _cipher() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    return _cipher().decrypt(value.encode("ascii")).decode("utf-8")

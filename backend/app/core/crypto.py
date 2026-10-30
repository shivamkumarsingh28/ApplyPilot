"""Encryption at rest for user documents and profile data.

Uses Fernet (AES-128-CBC + HMAC). In production set ENCRYPTION_KEY explicitly.
In development, a key is derived from SECRET_KEY so the app starts with zero setup.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    if settings.encryption_key:
        return Fernet(settings.encryption_key.encode())
    if settings.app_env == "production":
        raise RuntimeError("ENCRYPTION_KEY must be set in production")
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(derived)


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return _fernet().decrypt(token)


def encrypt_text(text: str) -> str:
    return encrypt_bytes(text.encode()).decode()


def decrypt_text(token: str) -> str:
    return decrypt_bytes(token.encode()).decode()

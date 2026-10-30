"""Encrypted file storage on local disk.

Swap this module for an S3/OCI Object Storage implementation in production; the
rest of the app only uses `save_file` and `load_file`.
"""

import os
import uuid

from app.core.config import get_settings
from app.core.crypto import decrypt_bytes, encrypt_bytes


def save_file(user_id: int, data: bytes) -> str:
    """Encrypt and store bytes, returning a storage path relative to STORAGE_DIR."""
    rel = os.path.join(str(user_id), uuid.uuid4().hex + ".enc")
    full = os.path.join(get_settings().storage_dir, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as fh:
        fh.write(encrypt_bytes(data))
    return rel


def load_file(rel_path: str) -> bytes:
    full = os.path.join(get_settings().storage_dir, rel_path)
    with open(full, "rb") as fh:
        return decrypt_bytes(fh.read())


def delete_file(rel_path: str) -> None:
    full = os.path.join(get_settings().storage_dir, rel_path)
    if os.path.exists(full):
        os.remove(full)

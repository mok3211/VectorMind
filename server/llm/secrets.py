from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from server.config import settings


def _fernet() -> Fernet:
    raw = (settings.jwt_secret or "please_change_me").encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def mask_secret(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if len(v) <= 10:
        return v[:2] + "…" + v[-2:]
    return v[:4] + "…" + v[-4:]

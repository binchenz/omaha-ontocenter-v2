"""Symmetric encryption for sensitive datasource fields (passwords).

Uses Fernet (AES-128-CBC + HMAC) keyed by SECRET_KEY. Stored values are
non-deterministic ciphertext + integrity tag; decrypt failure raises.
"""
import base64
import hashlib
from cryptography.fernet import Fernet

from app.config import settings


_SENSITIVE_KEYS = ("password", "secret", "token")


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_str(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_str(ciphertext: str) -> str:
    """Decrypt a previously-encrypted string. Raises InvalidToken on failure.

    Fail-loud so SECRET_KEY rotation or DB corruption surfaces as a clear
    error rather than silently returning empty credentials.
    """
    if not ciphertext:
        return ""
    return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")


def encrypt_config(config: dict) -> dict:
    """Encrypt known-sensitive keys; leave others untouched."""
    out = dict(config)
    for k in _SENSITIVE_KEYS:
        if k in out and isinstance(out[k], str) and out[k]:
            out[k] = encrypt_str(out[k])
    return out


def decrypt_config(config: dict) -> dict:
    out = dict(config)
    for k in _SENSITIVE_KEYS:
        if k in out and isinstance(out[k], str) and out[k]:
            out[k] = decrypt_str(out[k])
    return out

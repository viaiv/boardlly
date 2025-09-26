from __future__ import annotations

import secrets
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _get_aes_gcm() -> AESGCM:
    return AESGCM(settings.encryption_key_bytes)


def encrypt_secret(secret: str) -> Tuple[bytes, bytes]:
    nonce = secrets.token_bytes(12)
    aes_gcm = _get_aes_gcm()
    ciphertext = aes_gcm.encrypt(nonce, secret.encode("utf-8"), None)
    return nonce, ciphertext


def decrypt_secret(nonce: bytes, ciphertext: bytes) -> str:
    aes_gcm = _get_aes_gcm()
    plaintext = aes_gcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")

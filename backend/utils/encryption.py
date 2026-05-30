"""
AES-256-GCM authenticated encryption for secrets at rest (SSH passwords/keys,
raw report snapshots).

The 256-bit key is derived from ``SSH_ENCRYPTION_MASTER_KEY`` in .env:
  * if the value is 64 hex chars (32 bytes) it is used directly;
  * otherwise it is run through SHA-256 to produce a deterministic 32-byte key.

Ciphertext format (URL-safe base64):  nonce(12 bytes) || ciphertext || tag(16 bytes)

SECURITY: this module never logs, prints, or otherwise emits key material or
plaintext. Decryption failures raise a generic error without echoing inputs.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import settings

_NONCE_BYTES = 12  # 96-bit nonce recommended for GCM


def _derive_key() -> bytes:
    raw = settings.SSH_ENCRYPTION_MASTER_KEY.strip()
    try:
        key = bytes.fromhex(raw)
        if len(key) == 32:
            return key
    except ValueError:
        pass
    # Fallback: deterministically derive a 32-byte key from the master secret.
    return hashlib.sha256(raw.encode("utf-8")).digest()


_KEY = _derive_key()


class EncryptionError(Exception):
    """Raised when encryption or decryption fails. Carries no sensitive data."""


def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string, returning URL-safe base64 (nonce||ct||tag)."""
    if plaintext is None:
        raise EncryptionError("plaintext must not be None")
    # Use a cryptographically secure random nonce (os.urandom via cryptography).
    import os

    nonce = os.urandom(_NONCE_BYTES)
    aesgcm = AESGCM(_KEY)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`. Raises EncryptionError on tamper."""
    try:
        blob = base64.urlsafe_b64decode(token.encode("ascii"))
        nonce, ct = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
        aesgcm = AESGCM(_KEY)
        return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
    except (InvalidTag, ValueError, KeyError) as exc:
        # Do not include the token or any derived value in the message.
        raise EncryptionError("Failed to decrypt value (invalid key or corrupted data)") from exc

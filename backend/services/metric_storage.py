"""
Helpers for encrypting/decrypting the JSON metric columns
(``running_processes`` and ``open_ports``) with AES-256-GCM.

Values are stored as an encrypted string inside the JSONB column. Readers must
decrypt before use. Both helpers tolerate legacy plaintext (list/dict) values.
"""
from __future__ import annotations

import json
from typing import Any

from utils.encryption import EncryptionError, decrypt, encrypt


def encrypt_json(value: Any) -> str | None:
    """Serialize a JSON-able value and encrypt it. None stays None."""
    if value is None:
        return None
    return encrypt(json.dumps(value))


def decrypt_json(stored: Any) -> Any:
    """Decrypt a stored value back to its JSON structure.

    Accepts the encrypted string we write, or legacy plaintext (list/dict).
    """
    if stored is None:
        return None
    if isinstance(stored, (list, dict)):
        return stored  # legacy plaintext row
    if isinstance(stored, str):
        try:
            return json.loads(decrypt(stored))
        except (EncryptionError, json.JSONDecodeError, ValueError):
            return None
    return None

"""
Data sanitization: redact secrets from collected metrics and logs before they
are stored or sent to the AI. Every redaction is recorded in audit_logs with
the server and field name — never the redacted value itself.
"""
from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from services.audit_service import record_event

logger = logging.getLogger("ai_infra.sanitizer")

REDACTED = "[REDACTED BY SANITIZER]"
REDACTION_EVENT = "data_redacted"

# Compiled redaction patterns.
_PATTERNS: list[re.Pattern] = [
    # Private key blocks (RSA / OPENSSH / EC / generic).
    re.compile(
        r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----.*?"
        r"-----END (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----",
        re.DOTALL,
    ),
    # Secrets in environment-variable style assignments.
    re.compile(r"(?:PASSWORD|PASSWD|SECRET|API_KEY|TOKEN)\s*=\s*\S+", re.IGNORECASE),
    # AWS access key IDs and access-key assignments.
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"aws_access_key[a-z_]*\s*=\s*\S+", re.IGNORECASE),
]


def _redact_string(value: str) -> tuple[str, bool]:
    """Return (sanitized, was_redacted)."""
    redacted = value
    for pattern in _PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted, (redacted != value)


def _walk(node: Any, path: str, redacted_fields: list[str]) -> Any:
    """Recursively sanitize strings within dicts/lists, tracking field paths."""
    if isinstance(node, str):
        new, changed = _redact_string(node)
        if changed:
            redacted_fields.append(path or "<root>")
        return new
    if isinstance(node, dict):
        return {k: _walk(v, f"{path}.{k}" if path else str(k), redacted_fields) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v, f"{path}[{i}]", redacted_fields) for i, v in enumerate(node)]
    return node


async def _audit_redactions(
    db: AsyncSession | None,
    server_id: uuid.UUID | str | None,
    fields: list[str],
) -> None:
    if not db or not fields:
        return
    for field in fields:
        await record_event(
            db,
            event_type=REDACTION_EVENT,
            success=True,
            target_server_id=server_id,
            description=f"Sensitive data redacted from field '{field}' before storage/AI.",
        )
    logger.warning("Redacted %d field(s) during sanitization", len(fields))


async def sanitize_metrics(
    raw_data: dict,
    *,
    db: AsyncSession | None = None,
    server_id: uuid.UUID | str | None = None,
) -> dict:
    """Sanitize a metrics dict in place-safe manner, returning a clean copy."""
    redacted_fields: list[str] = []
    sanitized = _walk(raw_data, "", redacted_fields)
    await _audit_redactions(db, server_id, redacted_fields)
    return sanitized


async def sanitize_logs(
    raw_logs: list[dict] | list[str],
    *,
    db: AsyncSession | None = None,
    server_id: uuid.UUID | str | None = None,
) -> list:
    """Sanitize collected log entries (list of dicts or raw strings)."""
    redacted_fields: list[str] = []
    sanitized = _walk(raw_logs, "logs", redacted_fields)
    await _audit_redactions(db, server_id, redacted_fields)
    return sanitized

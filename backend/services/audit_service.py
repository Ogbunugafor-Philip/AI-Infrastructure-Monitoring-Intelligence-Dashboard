"""Helper for writing structured entries to the audit_logs table."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog


async def record_event(
    db: AsyncSession,
    *,
    event_type: str,
    success: bool,
    description: str | None = None,
    user_id: uuid.UUID | str | None = None,
    ip_address: str | None = None,
    target_server_id: uuid.UUID | str | None = None,
) -> None:
    """Append an audit entry. The caller controls transaction commit."""
    db.add(
        AuditLog(
            user_id=user_id,
            event_type=event_type,
            event_description=description,
            ip_address=ip_address,
            target_server_id=target_server_id,
            success=success,
        )
    )
    await db.flush()

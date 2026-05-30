"""Celery task that expires stale pending actions (runs every 60s)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from celery_app import celery_app
from models.enums import ActionStatus
from models.pending_action import PendingAction
from services.audit_service import record_event
from tasks.db import task_session


@celery_app.task(name="expire_pending_actions")
def expire_pending_actions_task() -> dict:
    """Mark pending / awaiting-confirmation actions past their expiry as expired."""
    async def _impl():
        now = datetime.now(timezone.utc)
        async with task_session() as db:
            rows = (
                await db.execute(
                    select(PendingAction).where(
                        PendingAction.status.in_([
                            ActionStatus.pending,
                            ActionStatus.awaiting_second_confirmation,
                        ]),
                        PendingAction.expires_at < now,
                    )
                )
            ).scalars().all()
            for action in rows:
                action.status = ActionStatus.expired
                await record_event(
                    db, event_type="action_expired", success=False,
                    user_id=action.requested_by_user_id, target_server_id=action.server_id,
                    description=f"Action {action.id} ({action.command_key}) expired (past expires_at).",
                )
            await db.commit()
            return {"expired": len(rows)}

    return asyncio.run(_impl())

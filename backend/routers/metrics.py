"""
Metrics router.

Endpoints (under /api/v1/metrics):
  GET  /{server_id}/latest                  - most recent metric (any authenticated)
  GET  /{server_id}/history                 - time-series for last N hours (any auth)
  POST /{server_id}/refresh                 - queue a full scan via Celery (admin+)
  GET  /{server_id}/refresh/{task_id}/status- poll Celery task status (any auth)

The manual refresh dispatches ``full_server_scan_task`` (collect metrics -> logs
-> AI analysis) and returns a task_id for polling. Encrypted metric JSON columns
are decrypted before being returned. Decrypted secrets are never logged.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from celery_app import celery_app
from database import get_db
from middleware.rbac import require_admin, require_viewer
from models.metric import Metric
from models.server import Server
from models.user import User
from schemas.metric import (
    MetricHistoryPoint,
    MetricHistoryResponse,
    MetricOut,
    RefreshDispatchResponse,
    TaskStatusResponse,
)
from services import audit_service
from services.metric_storage import decrypt_json
from tasks.metric_tasks import full_server_scan_task

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

MANUAL_REFRESH_EVENT = "manual_metric_refresh"


async def _get_server_or_404(db: AsyncSession, server_id: uuid.UUID) -> Server:
    server = (
        await db.execute(select(Server).where(Server.id == server_id))
    ).scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return server


def _metric_out(metric: Metric) -> MetricOut:
    """Build a MetricOut with the encrypted JSON columns decrypted."""
    out = MetricOut.model_validate(metric)
    out.running_processes = decrypt_json(metric.running_processes)
    out.open_ports = decrypt_json(metric.open_ports)
    return out


@router.get("/{server_id}/latest", response_model=MetricOut | None)
async def latest_metric(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> MetricOut | None:
    await _get_server_or_404(db, server_id)
    metric = (
        await db.execute(
            select(Metric)
            .where(Metric.server_id == server_id)
            .order_by(Metric.collected_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return _metric_out(metric) if metric else None


@router.get("/{server_id}/history", response_model=MetricHistoryResponse)
async def metric_history(
    server_id: uuid.UUID,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> MetricHistoryResponse:
    await _get_server_or_404(db, server_id)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = (
        await db.execute(
            select(Metric)
            .where(Metric.server_id == server_id, Metric.collected_at >= since)
            .order_by(Metric.collected_at.asc())
        )
    ).scalars().all()
    return MetricHistoryResponse(
        server_id=server_id,
        hours=hours,
        points=[
            MetricHistoryPoint(
                collected_at=m.collected_at,
                cpu_usage=m.cpu_usage,
                ram_usage=m.ram_usage,
                disk_usage=m.disk_usage,
            )
            for m in rows
        ],
    )


@router.post("/{server_id}/refresh", response_model=RefreshDispatchResponse)
async def refresh_metrics(
    request: Request,
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # viewer -> 403
) -> RefreshDispatchResponse:
    server = await _get_server_or_404(db, server_id)

    # Dispatch the full scan (metrics -> logs -> AI) to Celery.
    task = full_server_scan_task.delay(str(server_id))

    await audit_service.record_event(
        db,
        event_type=MANUAL_REFRESH_EVENT,
        success=True,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        target_server_id=server.id,
        description=f"Manual metric refresh queued for '{server.name}' (task {task.id}).",
    )
    await db.commit()

    return RefreshDispatchResponse(
        task_id=task.id,
        status="queued",
        message="Full server scan queued. Poll the status endpoint for completion.",
    )


@router.get("/{server_id}/refresh/{task_id}/status", response_model=TaskStatusResponse)
async def refresh_status(
    server_id: uuid.UUID,
    task_id: str,
    current_user: User = Depends(require_viewer),
) -> TaskStatusResponse:
    result = celery_app.AsyncResult(task_id)
    payload = None
    if result.successful():
        try:
            payload = result.result if isinstance(result.result, dict) else {"value": str(result.result)}
        except Exception:  # noqa: BLE001
            payload = None
    return TaskStatusResponse(
        task_id=task_id,
        state=result.state,
        ready=result.ready(),
        successful=result.successful() if result.ready() else None,
        result=payload,
    )

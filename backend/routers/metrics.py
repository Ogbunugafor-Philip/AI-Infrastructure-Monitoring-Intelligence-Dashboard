"""
Metrics router.

Endpoints (under /api/v1/metrics):
  GET  /{server_id}/latest   - most recent metric snapshot (any authenticated)
  GET  /{server_id}/history  - time-series for the last N hours (any authenticated)
  POST /{server_id}/refresh  - collect fresh metrics over SSH and store them

``refresh`` decrypts the server's stored credentials, gathers real metrics via
the SSH metrics collector, persists a new ``metrics`` row, and updates the
server's status. Connection/credential errors degrade gracefully and mark the
server offline. Decrypted secrets are never logged or returned.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.rbac import require_viewer
from models.enums import ServerStatus
from models.metric import Metric
from models.server import Server
from models.user import User
from schemas.metric import (
    MetricHistoryPoint,
    MetricHistoryResponse,
    MetricOut,
    RefreshResponse,
)
from services.metrics_service import collect_metrics
from services.ssh_service import SSHConnectionParams
from utils.encryption import EncryptionError, decrypt

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


async def _get_server_or_404(db: AsyncSession, server_id: uuid.UUID) -> Server:
    server = (
        await db.execute(select(Server).where(Server.id == server_id))
    ).scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return server


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
    return MetricOut.model_validate(metric) if metric else None


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


@router.post("/{server_id}/refresh", response_model=RefreshResponse)
async def refresh_metrics(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> RefreshResponse:
    server = await _get_server_or_404(db, server_id)

    # Decrypt stored credentials (never logged).
    password = key = None
    try:
        if server.encrypted_ssh_password:
            password = decrypt(server.encrypted_ssh_password)
        if server.encrypted_ssh_key:
            key = decrypt(server.encrypted_ssh_key)
    except EncryptionError:
        raise HTTPException(status_code=500, detail="Stored credential could not be decrypted")

    params = SSHConnectionParams(
        host=server.ip_address,
        port=server.ssh_port,
        username=server.ssh_username,
        auth_method=server.ssh_auth_method,
        password=password,
        private_key=key,
        key_only_mode=server.ssh_key_only_mode,
    )

    try:
        collected = await collect_metrics(params)
    except Exception as exc:  # noqa: BLE001 - any SSH/parse failure marks offline
        server.status = ServerStatus.offline
        await db.commit()
        return RefreshResponse(
            success=False,
            message=f"Metric collection failed ({type(exc).__name__}); server marked offline.",
        )

    metric = Metric(
        server_id=server.id,
        cpu_usage=collected.cpu_usage,
        ram_usage=collected.ram_usage,
        disk_usage=collected.disk_usage,
        uptime=collected.uptime,
        running_processes=collected.running_processes,
        open_ports=collected.open_ports,
        network_stats=collected.network_stats,
    )
    db.add(metric)

    # Derive status from the worst resource utilisation.
    worst = max(
        v for v in [collected.cpu_usage or 0, collected.ram_usage or 0, collected.disk_usage or 0]
    )
    server.status = ServerStatus.warning if worst >= 80 else ServerStatus.online

    await db.flush()
    await db.commit()
    await db.refresh(metric)
    return RefreshResponse(
        success=True,
        message="Metrics collected successfully.",
        metric=MetricOut.model_validate(metric),
    )

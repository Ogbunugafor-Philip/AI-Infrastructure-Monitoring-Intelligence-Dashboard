"""
Dashboard aggregation router.

Endpoints (under /api/v1/dashboard):
  GET /overview          - high-level counts & averages (any authenticated)
  GET /servers/status    - per-server status + latest metrics (any authenticated)
  GET /security-alerts   - recent security events with severity (admin+)
  GET /audit-logs        - paginated, filterable audit log (super_admin)
  GET /audit-logs/export - full audit log as CSV download (super_admin)

RBAC is enforced via dependencies that reject unauthorized roles with 403
*before* the handler body runs any business query.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.rbac import require_admin, require_super_admin, require_viewer
from models.audit_log import AuditLog
from models.enums import ServerStatus
from models.metric import Metric
from models.server import Server
from models.user import User
from schemas.dashboard import (
    AuditLogItem,
    AuditLogPage,
    OverviewResponse,
    SecurityAlert,
    ServerStatusItem,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# Security-relevant event types (spec names + the names actually emitted by the app).
SECURITY_EVENT_TYPES = {
    "failed_login", "login_failed",
    "intrusion_detected",
    "unauthorized_access",
    "credential_reveal",
    "ssh_connection_failed",
    "suspicious_activity",
    "ip_whitelist_denied",
    "password_reverify",
}
_HIGH = {"intrusion_detected", "unauthorized_access", "suspicious_activity", "ip_whitelist_denied"}
_MEDIUM = {
    "failed_login", "login_failed", "ssh_connection_failed",
    "ssh_connection_attempt", "credential_reveal", "password_reverify",
}


def _severity_for(event_type: str) -> str:
    if event_type in _HIGH:
        return "high"
    if event_type in _MEDIUM:
        return "medium"
    return "low"


def _utc_24h_ago() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=24)


def _latest_metric_subquery():
    """A subquery selecting the most recent metric row id per server."""
    return (
        select(Metric.server_id, func.max(Metric.collected_at).label("max_at"))
        .group_by(Metric.server_id)
        .subquery()
    )


# --------------------------------------------------------------------------- #
# Overview                                                                     #
# --------------------------------------------------------------------------- #
@router.get("/overview", response_model=OverviewResponse)
async def overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> OverviewResponse:
    total = (await db.execute(select(func.count()).select_from(Server))).scalar_one()

    status_counts = dict(
        (
            await db.execute(select(Server.status, func.count()).group_by(Server.status))
        ).all()
    )

    # Average over the latest metric per server.
    sub = _latest_metric_subquery()
    latest = (
        select(Metric.cpu_usage, Metric.ram_usage, Metric.disk_usage)
        .join(
            sub,
            and_(Metric.server_id == sub.c.server_id, Metric.collected_at == sub.c.max_at),
        )
        .subquery()
    )
    avgs = (
        await db.execute(
            select(
                func.coalesce(func.avg(latest.c.cpu_usage), 0.0),
                func.coalesce(func.avg(latest.c.ram_usage), 0.0),
                func.coalesce(func.avg(latest.c.disk_usage), 0.0),
            )
        )
    ).one()

    since = _utc_24h_ago()
    sec_alerts = (
        await db.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.event_type.in_(SECURITY_EVENT_TYPES), AuditLog.created_at >= since)
        )
    ).scalar_one()
    audit_events = (
        await db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= since)
        )
    ).scalar_one()

    return OverviewResponse(
        total_servers=total,
        servers_online=status_counts.get(ServerStatus.online, 0),
        servers_offline=status_counts.get(ServerStatus.offline, 0),
        servers_warning=status_counts.get(ServerStatus.warning, 0),
        avg_cpu_usage=round(float(avgs[0]), 1),
        avg_ram_usage=round(float(avgs[1]), 1),
        avg_disk_usage=round(float(avgs[2]), 1),
        security_alerts_24h=sec_alerts,
        audit_events_24h=audit_events,
    )


# --------------------------------------------------------------------------- #
# Per-server status                                                            #
# --------------------------------------------------------------------------- #
@router.get("/servers/status", response_model=list[ServerStatusItem])
async def servers_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> list[ServerStatusItem]:
    sub = _latest_metric_subquery()
    rows = (
        await db.execute(
            select(Server, Metric)
            .outerjoin(sub, sub.c.server_id == Server.id)
            .outerjoin(
                Metric,
                and_(Metric.server_id == sub.c.server_id, Metric.collected_at == sub.c.max_at),
            )
            .order_by(Server.created_at.desc())
        )
    ).all()

    items: list[ServerStatusItem] = []
    for server, metric in rows:
        items.append(
            ServerStatusItem(
                id=server.id,
                name=server.name,
                ip_address=server.ip_address,
                ssh_port=server.ssh_port,
                ssh_username=server.ssh_username,
                ssh_auth_method=server.ssh_auth_method,
                ssh_key_only_mode=server.ssh_key_only_mode,
                status=server.status,
                cpu_usage=metric.cpu_usage if metric else None,
                ram_usage=metric.ram_usage if metric else None,
                disk_usage=metric.disk_usage if metric else None,
                uptime=metric.uptime if metric else None,
                last_updated=metric.collected_at if metric else None,
            )
        )
    return items


# --------------------------------------------------------------------------- #
# Security alerts (admin+)                                                     #
# --------------------------------------------------------------------------- #
@router.get("/security-alerts", response_model=list[SecurityAlert])
async def security_alerts(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[SecurityAlert]:
    rows = (
        await db.execute(
            select(AuditLog)
            .where(
                or_(
                    AuditLog.event_type.in_(SECURITY_EVENT_TYPES),
                    and_(
                        AuditLog.event_type == "ssh_connection_attempt",
                        AuditLog.success.is_(False),
                    ),
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    return [
        SecurityAlert(
            id=r.id,
            event_type=r.event_type,
            event_description=r.event_description,
            ip_address=r.ip_address,
            user_id=r.user_id,
            target_server_id=r.target_server_id,
            success=r.success,
            severity=_severity_for(r.event_type),
            created_at=r.created_at,
        )
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# Audit logs (super_admin) — paginated + filterable                           #
# --------------------------------------------------------------------------- #
def _audit_filters(
    event_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    user_id: uuid.UUID | None,
    server_id: uuid.UUID | None,
):
    conds = []
    if event_type:
        conds.append(AuditLog.event_type == event_type)
    if date_from:
        conds.append(AuditLog.created_at >= date_from)
    if date_to:
        conds.append(AuditLog.created_at <= date_to)
    if user_id:
        conds.append(AuditLog.user_id == user_id)
    if server_id:
        conds.append(AuditLog.target_server_id == server_id)
    return conds


@router.get("/audit-logs", response_model=AuditLogPage)
async def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id: uuid.UUID | None = None,
    server_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> AuditLogPage:
    conds = _audit_filters(event_type, date_from, date_to, user_id, server_id)

    total = (
        await db.execute(select(func.count()).select_from(AuditLog).where(*conds))
    ).scalar_one()

    rows = (
        await db.execute(
            select(AuditLog)
            .where(*conds)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    total_pages = (total + page_size - 1) // page_size
    return AuditLogPage(
        items=[AuditLogItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/audit-logs/export")
async def export_audit_logs(
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id: uuid.UUID | None = None,
    server_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> StreamingResponse:
    conds = _audit_filters(event_type, date_from, date_to, user_id, server_id)
    rows = (
        await db.execute(
            select(AuditLog).where(*conds).order_by(AuditLog.created_at.desc())
        )
    ).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "created_at", "event_type", "success", "user_id",
        "target_server_id", "ip_address", "event_description",
    ])
    for r in rows:
        writer.writerow([
            str(r.id), r.created_at.isoformat(), r.event_type, r.success,
            str(r.user_id or ""), str(r.target_server_id or ""),
            r.ip_address or "", (r.event_description or "").replace("\n", " "),
        ])
    buffer.seek(0)

    filename = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

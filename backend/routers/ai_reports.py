"""
AI reports router.

Endpoints (under /api/v1/ai-reports):
  GET  /{server_id}/latest    - most recent AI report (any authenticated)
  GET  /{server_id}/history   - paginated past reports (any authenticated)
  POST /{server_id}/generate  - queue a new AI analysis via Celery (admin+)

Reports expose summary/findings/recommendations (already plaintext); the
encrypted ``raw_data_snapshot`` is never returned.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.rbac import require_admin, require_viewer
from models.ai_report import AIReport
from models.server import Server
from models.user import User
from schemas.ai_report import (
    AIReportHistoryItem,
    AIReportHistoryPage,
    AIReportOut,
    GenerateResponse,
)
from services import audit_service
from tasks.metric_tasks import analyze_server_task

router = APIRouter(prefix="/api/v1/ai-reports", tags=["ai-reports"])

GENERATE_EVENT = "ai_report_generate"


async def _ensure_server(db: AsyncSession, server_id: uuid.UUID) -> Server:
    server = (
        await db.execute(select(Server).where(Server.id == server_id))
    ).scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return server


@router.get("/{server_id}/latest", response_model=AIReportOut | None)
async def latest_report(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> AIReportOut | None:
    await _ensure_server(db, server_id)
    report = (
        await db.execute(
            select(AIReport).where(AIReport.server_id == server_id)
            .order_by(AIReport.generated_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return AIReportOut.model_validate(report) if report else None


@router.get("/{server_id}/history", response_model=AIReportHistoryPage)
async def report_history(
    server_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> AIReportHistoryPage:
    await _ensure_server(db, server_id)
    total = (
        await db.execute(
            select(func.count()).select_from(AIReport).where(AIReport.server_id == server_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(AIReport).where(AIReport.server_id == server_id)
            .order_by(AIReport.generated_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return AIReportHistoryPage(
        items=[AIReportHistoryItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/{server_id}/generate", response_model=GenerateResponse)
async def generate_report(
    request: Request,
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # viewer -> 403
) -> GenerateResponse:
    server = await _ensure_server(db, server_id)
    task = analyze_server_task.delay(str(server_id))

    await audit_service.record_event(
        db,
        event_type=GENERATE_EVENT,
        success=True,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        target_server_id=server.id,
        description=f"AI report generation queued for '{server.name}' (task {task.id}).",
    )
    await db.commit()

    return GenerateResponse(
        task_id=task.id,
        status="queued",
        message="AI analysis queued. Poll the metrics refresh status endpoint or reload reports.",
    )

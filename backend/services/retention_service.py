"""
Data retention enforcement.

Deletes records older than the configured retention windows (from .env):
  * metrics    older than METRICS_RETENTION_DAYS
  * logs       older than LOGS_RETENTION_DAYS
  * ai_reports older than AI_REPORTS_RETENTION_DAYS
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.ai_report import AIReport
from models.log import Log
from models.metric import Metric

logger = logging.getLogger("ai_infra.retention")


def _cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def run_retention(db: AsyncSession) -> dict[str, int]:
    """Delete expired metrics/logs/ai_reports. Returns per-table delete counts."""
    metrics_cut = _cutoff(settings.METRICS_RETENTION_DAYS)
    logs_cut = _cutoff(settings.LOGS_RETENTION_DAYS)
    reports_cut = _cutoff(settings.AI_REPORTS_RETENTION_DAYS)

    m = await db.execute(delete(Metric).where(Metric.collected_at < metrics_cut))
    l = await db.execute(delete(Log).where(Log.collected_at < logs_cut))
    r = await db.execute(delete(AIReport).where(AIReport.generated_at < reports_cut))
    await db.commit()

    counts = {
        "metrics_deleted": m.rowcount or 0,
        "logs_deleted": l.rowcount or 0,
        "ai_reports_deleted": r.rowcount or 0,
    }
    logger.info(
        "Retention cleanup: metrics=%(metrics_deleted)d logs=%(logs_deleted)d "
        "ai_reports=%(ai_reports_deleted)d", counts,
    )
    return counts

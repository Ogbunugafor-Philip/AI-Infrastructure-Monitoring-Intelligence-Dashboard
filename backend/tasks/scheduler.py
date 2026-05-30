"""
APScheduler (AsyncIOScheduler) running inside the FastAPI process.

Schedules:
  * scan_all_servers      - every SCHEDULER_REPORT_INTERVAL_HOURS (.env)
  * retention_cleanup     - daily at 03:00 UTC

The scheduled jobs simply dispatch Celery tasks (.delay), so the heavy work runs
in the Celery worker, not the web process.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from tasks.metric_tasks import run_retention_cleanup_task, scan_all_servers_task

logger = logging.getLogger("ai_infra.scheduler")

scheduler = AsyncIOScheduler(timezone="UTC")


def _dispatch_scan_all() -> None:
    scan_all_servers_task.delay()
    logger.info("Dispatched scheduled scan_all_servers task")


def _dispatch_retention() -> None:
    run_retention_cleanup_task.delay()
    logger.info("Dispatched scheduled retention cleanup task")


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _dispatch_scan_all,
        IntervalTrigger(hours=settings.SCHEDULER_REPORT_INTERVAL_HOURS),
        id="scan_all_servers",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        _dispatch_retention,
        CronTrigger(hour=3, minute=0),  # 03:00 UTC daily
        id="retention_cleanup",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: scan every %dh, retention daily at 03:00 UTC",
        settings.SCHEDULER_REPORT_INTERVAL_HOURS,
    )


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def list_jobs() -> list[dict]:
    """Introspection helper for verification/health checks."""
    return [
        {"id": job.id, "next_run_time": str(job.next_run_time), "trigger": str(job.trigger)}
        for job in scheduler.get_jobs()
    ]

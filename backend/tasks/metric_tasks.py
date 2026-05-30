"""
Celery tasks for metric collection, log collection, AI analysis, retention, and
full server scans. Each task runs its async implementation via ``asyncio.run``
with a fresh per-task DB session.
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from celery_app import celery_app
from models.enums import ServerStatus
from models.log import Log
from models.metric import Metric
from models.server import Server
from services.ai_analysis_service import analyze_server
from services.data_sanitizer import sanitize_logs, sanitize_metrics
from services.log_collector import collect_logs
from services.metric_collector import collect_all_metrics
from services.metric_storage import encrypt_json
from services.report_email_service import send_daily_report_email
from services.retention_service import run_retention
from tasks.db import task_session
from utils.encryption import encrypt


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# Core async implementations                                                   #
# --------------------------------------------------------------------------- #
async def _store_metrics(db, server_id) -> dict:
    raw = await collect_all_metrics(db, server_id)
    clean = await sanitize_metrics(raw, db=db, server_id=server_id)

    metric = Metric(
        server_id=server_id,
        cpu_usage=clean.get("cpu_usage"),
        ram_usage=clean.get("ram_usage"),
        disk_usage=clean.get("disk_usage"),
        uptime=clean.get("uptime"),
        # Encrypted JSON columns (AES-256-GCM).
        running_processes=encrypt_json(clean.get("running_processes")),
        open_ports=encrypt_json(clean.get("open_ports")),
        # Extended context kept (sanitized) in network_stats JSONB.
        network_stats={
            "interfaces": clean.get("network_stats"),
            "load_average": clean.get("load_average"),
            "kernel_version": clean.get("kernel_version"),
            "os_info": clean.get("os_info"),
            "disk_per_mount": clean.get("disk_per_mount"),
            "logged_in_users": clean.get("logged_in_users"),
            "failed_logins": clean.get("failed_logins"),
        },
    )
    db.add(metric)

    # Update server status from worst resource utilisation.
    server = (await db.execute(select(Server).where(Server.id == server_id))).scalar_one_or_none()
    if server is not None:
        worst = max(
            clean.get("cpu_usage") or 0,
            clean.get("ram_usage") or 0,
            clean.get("disk_usage") or 0,
        )
        server.status = ServerStatus.warning if worst >= 80 else ServerStatus.online

    await db.commit()
    await db.refresh(metric)
    return {"status": "ok", "metric_id": str(metric.id)}


async def _store_logs(db, server_id) -> dict:
    entries = await collect_logs(db, server_id)
    clean = await sanitize_logs(entries, db=db, server_id=server_id)
    for e in clean:
        db.add(
            Log(
                server_id=server_id,
                log_source=e["log_source"],
                log_level=e["log_level"],
                raw_line=encrypt(e["raw_line"]),  # encrypted at rest
                parsed_timestamp=e.get("parsed_timestamp"),
            )
        )
    await db.commit()
    return {"status": "ok", "count": len(clean)}


async def _do_analysis(db, server_id) -> dict:
    report = await analyze_server(db, server_id)
    server = (await db.execute(select(Server).where(Server.id == server_id))).scalar_one_or_none()
    report_dict = {
        "summary": report.summary,
        "risk_score": report.risk_score,
        "risk_level": report.risk_level,
        "key_findings": report.key_findings,
        "recommended_actions": report.recommended_actions,
        "security_observations": report.security_observations,
        "performance_observations": report.performance_observations,
    }
    if server is not None:
        await send_daily_report_email(db, server, report_dict)
    return {
        "status": "ok",
        "report_id": str(report.id),
        "risk_score": report.risk_score,
        "risk_level": report.risk_level,
    }


# --------------------------------------------------------------------------- #
# Celery tasks                                                                 #
# --------------------------------------------------------------------------- #
@celery_app.task(name="collect_server_metrics")
def collect_server_metrics_task(server_id: str) -> dict:
    async def _impl():
        async with task_session() as db:
            return await _store_metrics(db, server_id)
    return _run(_impl())


@celery_app.task(name="collect_server_logs")
def collect_server_logs_task(server_id: str) -> dict:
    async def _impl():
        async with task_session() as db:
            return await _store_logs(db, server_id)
    return _run(_impl())


@celery_app.task(name="analyze_server")
def analyze_server_task(server_id: str) -> dict:
    async def _impl():
        async with task_session() as db:
            return await _do_analysis(db, server_id)
    return _run(_impl())


@celery_app.task(name="full_server_scan")
def full_server_scan_task(server_id: str) -> dict:
    """Collect metrics -> collect logs -> analyze, in order, in one task."""
    async def _impl():
        results = {}
        async with task_session() as db:
            results["metrics"] = await _store_metrics(db, server_id)
        async with task_session() as db:
            results["logs"] = await _store_logs(db, server_id)
        async with task_session() as db:
            results["analysis"] = await _do_analysis(db, server_id)
        return {"status": "ok", "server_id": str(server_id), "results": results}
    return _run(_impl())


@celery_app.task(name="scan_all_servers")
def scan_all_servers_task() -> dict:
    """Dispatch a full scan for every registered server."""
    async def _server_ids():
        async with task_session() as db:
            rows = (await db.execute(select(Server.id))).scalars().all()
            return [str(r) for r in rows]

    ids = _run(_server_ids())
    for sid in ids:
        full_server_scan_task.delay(sid)
    return {"status": "ok", "dispatched": len(ids)}


@celery_app.task(name="run_retention_cleanup")
def run_retention_cleanup_task() -> dict:
    async def _impl():
        async with task_session() as db:
            return await run_retention(db)
    return _run(_impl())

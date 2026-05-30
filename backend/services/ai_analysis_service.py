"""
Cerebras AI analysis.

``analyze_server(db, server_id)`` gathers the latest metrics + recent logs,
decrypts the encrypted columns, runs a final sanitization pass, builds the exact
prompt, calls the Cerebras chat API, parses the JSON response (with a safe
fallback), and stores an ``ai_reports`` row whose ``raw_data_snapshot`` is
AES-256-GCM encrypted. The unencrypted prompt / raw data is never persisted.
"""
from __future__ import annotations

import ast
import re
import asyncio
import json
import logging
import uuid

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.ai_report import AIReport
from models.enums import ReportType
from models.log import Log
from models.metric import Metric
from models.server import Server
from services.data_sanitizer import sanitize_metrics
from services.metric_storage import decrypt_json
from utils.encryption import decrypt, encrypt

logger = logging.getLogger("ai_infra.ai_analysis")

CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
REQUEST_TIMEOUT = 60


def _build_prompt(ctx: dict) -> str:
    """Build the exact specified prompt from the sanitized context."""
    return (
        "You are an expert Linux infrastructure engineer and security analyst. "
        "Analyze the following server metrics and logs and provide a clear "
        "infrastructure health report.\n\n"
        f"Server IP: {ctx['server_ip']}\n"
        f"Collection Time: {ctx['collected_at']}\n\n"
        "SYSTEM METRICS:\n"
        f"CPU Usage: {ctx['cpu_usage']}%\n"
        f"RAM Usage: {ctx['ram_usage']}%\n"
        f"Disk Usage: {ctx['disk_usage']}\n"
        f"System Uptime: {ctx['uptime']}\n"
        f"Load Average: {ctx['load_average']}\n"
        f"Kernel Version: {ctx['kernel_version']}\n"
        f"OS: {ctx['os_info']}\n\n"
        "TOP PROCESSES:\n"
        f"{ctx['running_processes']}\n\n"
        "OPEN PORTS:\n"
        f"{ctx['open_ports']}\n\n"
        "NETWORK STATISTICS:\n"
        f"{ctx['network_stats']}\n\n"
        "RECENT SYSTEM LOGS (last 50 lines):\n"
        f"{ctx['syslog_entries']}\n\n"
        "RECENT AUTH LOGS (last 50 lines):\n"
        f"{ctx['auth_log_entries']}\n\n"
        "Based on this data, provide your response in this exact JSON format "
        "with no additional text:\n"
        "{\n"
        "  'summary': 'A 3-5 sentence plain English summary of the server health condition',\n"
        "  'risk_score': A number from 1 to 10 where 1 is healthy and 10 is critical,\n"
        "  'risk_level': 'healthy or warning or critical',\n"
        "  'key_findings': ['finding 1', 'finding 2', 'finding 3'],\n"
        "  'recommended_actions': ['action 1', 'action 2', 'action 3'],\n"
        "  'security_observations': ['observation 1', 'observation 2'],\n"
        "  'performance_observations': ['observation 1', 'observation 2']\n"
        "}"
    )


def _call_cerebras(prompt: str) -> str:
    """Blocking Cerebras chat completion. Returns the message content string."""
    resp = requests.post(
        CEREBRAS_URL,
        headers={
            "Authorization": f"Bearer {settings.CEREBRAS_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.CEREBRAS_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": settings.CEREBRAS_MAX_TOKENS,
            "temperature": 0.2,
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


_LIST_FIELDS = (
    "key_findings", "recommended_actions",
    "security_observations", "performance_observations",
)

_PARSE_ERROR_REPORT = {
    "summary": "AI analysis could not be parsed. Raw response stored.",
    "risk_score": 5,
    "risk_level": "warning",
    "key_findings": [],
    "recommended_actions": [],
    "security_observations": [],
    "performance_observations": [],
}


def _normalize_report(data: dict) -> dict:
    """Guarantee a complete, well-typed report dict (lists for list fields)."""
    out = {
        "summary": str(data.get("summary") or "").strip() or "No summary provided.",
        "risk_score": data.get("risk_score", 5),
        "risk_level": data.get("risk_level") or "warning",
    }
    for field in _LIST_FIELDS:
        value = data.get(field)
        if isinstance(value, list):
            out[field] = [str(v) for v in value]
        elif value in (None, ""):
            out[field] = []
        else:
            out[field] = [str(value)]
    return out


def _coerce_report(content: str) -> dict:
    """
    Parse the model output into a normalized report dict.

    Strips markdown fences and whitespace, tries strict JSON, then a
    single-quote→double-quote pass, then ast.literal_eval (Python-dict format).
    If everything fails, returns a structured error object — NEVER the raw text.
    """
    text = (content or "").strip()
    # Strip markdown code fences (```json ... ```).
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    # Narrow to the outermost {...} block when possible.
    start, end = text.find("{"), text.rfind("}")
    block = text[start : end + 1] if start != -1 and end != -1 else text

    candidates = [block, text, block.replace("'", '"')]
    for cand in candidates:
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                return _normalize_report(data)
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            data = ast.literal_eval(cand)
            if isinstance(data, dict):
                return _normalize_report(data)
        except (ValueError, SyntaxError, TypeError):
            pass

    # Structured error — a proper dict, never a raw JSON string in `summary`.
    return dict(_PARSE_ERROR_REPORT)


def _clamp_risk(value) -> int:
    try:
        return max(1, min(10, int(float(value))))
    except (TypeError, ValueError):
        return 5


async def analyze_server(db: AsyncSession, server_id: uuid.UUID | str) -> AIReport:
    """Run AI analysis for a server and persist an AIReport. Returns the row."""
    server = (
        await db.execute(select(Server).where(Server.id == server_id))
    ).scalar_one_or_none()
    if server is None:
        raise ValueError("Server not found")

    metric = (
        await db.execute(
            select(Metric).where(Metric.server_id == server_id)
            .order_by(Metric.collected_at.desc()).limit(1)
        )
    ).scalar_one_or_none()

    logs = (
        await db.execute(
            select(Log).where(Log.server_id == server_id)
            .order_by(Log.collected_at.desc()).limit(50)
        )
    ).scalars().all()

    # Decrypt encrypted columns before building the prompt.
    processes = decrypt_json(metric.running_processes) if metric else None
    ports = decrypt_json(metric.open_ports) if metric else None
    network = metric.network_stats if metric else None
    extra = network if isinstance(network, dict) else {}

    syslog_lines, auth_lines = [], []
    for lg in logs:
        try:
            line = decrypt(lg.raw_line)
        except Exception:  # noqa: BLE001
            line = "[unreadable]"
        if lg.log_source == "auth":
            auth_lines.append(line)
        else:
            syslog_lines.append(line)

    raw_context = {
        "server_ip": server.ip_address,
        "collected_at": str(metric.collected_at) if metric else "n/a",
        "cpu_usage": metric.cpu_usage if metric else "n/a",
        "ram_usage": metric.ram_usage if metric else "n/a",
        "disk_usage": metric.disk_usage if metric else "n/a",
        "uptime": metric.uptime if metric else "n/a",
        "load_average": extra.get("load_average") if metric else "n/a",
        "kernel_version": extra.get("kernel_version") if metric else "n/a",
        "os_info": extra.get("os_info") if metric else "n/a",
        "running_processes": processes,
        "open_ports": ports,
        "network_stats": network,
        "syslog_entries": "\n".join(syslog_lines[:50]) or "none",
        "auth_log_entries": "\n".join(auth_lines[:50]) or "none",
    }

    # Final sanitization pass on the decrypted data before sending to AI.
    ctx = await sanitize_metrics(raw_context, db=db, server_id=server_id)

    prompt = _build_prompt(ctx)

    # Call Cerebras; on any failure, degrade to a safe fallback report.
    try:
        content = await asyncio.to_thread(_call_cerebras, prompt)
        report = _coerce_report(content)
    except Exception as exc:  # noqa: BLE001
        logger.error("Cerebras call failed: %s", type(exc).__name__)
        report = {
            "summary": f"AI analysis unavailable ({type(exc).__name__}). "
                       "Metrics were collected but the AI service could not be reached.",
            "risk_score": 5,
            "risk_level": "warning",
            "key_findings": [],
            "recommended_actions": ["Verify Cerebras API connectivity and credentials."],
            "security_observations": [],
            "performance_observations": [],
        }

    ai_report = AIReport(
        server_id=server.id,
        summary=report.get("summary"),
        risk_score=_clamp_risk(report.get("risk_score", 5)),
        risk_level=report.get("risk_level"),
        recommended_actions=report.get("recommended_actions") or [],
        key_findings=report.get("key_findings") or [],
        security_observations=report.get("security_observations") or [],
        performance_observations=report.get("performance_observations") or [],
        # Encrypt the raw (sanitized) snapshot; never store plaintext prompt/data.
        raw_data_snapshot=encrypt(json.dumps(ctx, default=str)),
        report_type=ReportType.manual,
    )
    db.add(ai_report)
    await db.commit()
    await db.refresh(ai_report)
    return ai_report

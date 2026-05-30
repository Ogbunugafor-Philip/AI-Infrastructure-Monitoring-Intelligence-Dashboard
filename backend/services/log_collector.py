"""
SSH-based log collection.

``collect_logs(db, server_id)`` reads a fixed set of log files over a single SSH
session using the safe pattern ``sudo tail -n {n} {path} 2>/dev/null || echo
"log_unavailable"``. Each line is parsed into (timestamp, level, source,
message). Unparseable lines are stored as raw text with level INFO.
Returns a list of dicts ready for storage.
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.server import Server
from services.ssh_service import build_params_from_server, open_ssh_client

logger = logging.getLogger("ai_infra.log_collector")

PER_COMMAND_TIMEOUT = 10
UNAVAILABLE = "log_unavailable"

# (source label, list of candidate paths, number of lines, is_glob)
LOG_SPECS = [
    ("syslog", ["/var/log/syslog", "/var/log/messages"], 100, False),
    ("auth", ["/var/log/auth.log", "/var/log/secure"], 100, False),
    ("nginx_error", ["/var/log/nginx/error.log"], 50, False),
    ("nginx_access", ["/var/log/nginx/access.log"], 50, False),
    ("postgresql", ["/var/log/postgresql/*.log"], 50, True),
]

_LEVEL_RE = re.compile(r"\b(ERROR|ERR|CRITICAL|FATAL|WARN(?:ING)?|INFO|DEBUG|NOTICE)\b", re.I)
# syslog "Mon DD HH:MM:SS" and ISO-8601 timestamps.
_SYSLOG_TS = re.compile(r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")
_ISO_TS = re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})")


def _read(client, path: str, lines: int) -> str | None:
    cmd = f'sudo tail -n {lines} {path} 2>/dev/null || echo "{UNAVAILABLE}"'
    try:
        _, stdout, _ = client.exec_command(cmd, timeout=PER_COMMAND_TIMEOUT)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        if not out or out == UNAVAILABLE:
            return None
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("log read failed for %s: %s", path, type(exc).__name__)
        return None


def _normalize_level(token: str) -> str:
    t = token.upper()
    if t in {"ERR", "ERROR", "CRITICAL", "FATAL"}:
        return "ERROR"
    if t in {"WARN", "WARNING", "NOTICE"}:
        return "WARN"
    if t == "DEBUG":
        return "DEBUG"
    return "INFO"


def _parse_timestamp(line: str) -> datetime | None:
    m = _ISO_TS.match(line)
    if m:
        try:
            return datetime.fromisoformat(m.group(1).replace(" ", "T"))
        except ValueError:
            return None
    m = _SYSLOG_TS.match(line)
    if m:
        try:
            # syslog lacks a year; assume current year.
            year = datetime.now(timezone.utc).year
            return datetime.strptime(f"{year} {m.group(1)}", "%Y %b %d %H:%M:%S")
        except ValueError:
            return None
    return None


def _parse_line(line: str, source: str) -> dict:
    level_match = _LEVEL_RE.search(line)
    level = _normalize_level(level_match.group(1)) if level_match else "INFO"
    ts = _parse_timestamp(line)
    return {
        "log_source": source,
        "log_level": level,
        "raw_line": line,
        "parsed_timestamp": ts,
    }


def _collect_blocking(params) -> list[dict]:
    entries: list[dict] = []
    with open_ssh_client(params) as client:
        # Discover app logs dynamically.
        specs = list(LOG_SPECS)
        try:
            _, stdout, _ = client.exec_command(
                'ls /var/log/app/*.log 2>/dev/null || echo ""', timeout=PER_COMMAND_TIMEOUT
            )
            app_files = [f for f in stdout.read().decode().split() if f.endswith(".log")]
            for f in app_files:
                specs.append(("app", [f], 50, False))
        except Exception:  # noqa: BLE001
            pass

        for source, paths, lines, _is_glob in specs:
            content = None
            for path in paths:
                content = _read(client, path, lines)
                if content is not None:
                    break
            if content is None:
                continue
            for raw in content.splitlines():
                if raw.strip():
                    entries.append(_parse_line(raw, source))
    return entries


async def collect_logs(db: AsyncSession, server_id: uuid.UUID | str) -> list[dict]:
    """Collect & parse logs from a server over SSH. Returns a list of entries."""
    server = (
        await db.execute(select(Server).where(Server.id == server_id))
    ).scalar_one_or_none()
    if server is None:
        raise ValueError("Server not found")

    params = build_params_from_server(server)
    return await asyncio.to_thread(_collect_blocking, params)

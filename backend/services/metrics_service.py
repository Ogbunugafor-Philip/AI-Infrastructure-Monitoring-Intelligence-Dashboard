"""
Real metric collection over SSH.

``collect_metrics`` opens an SSH session to a server and runs a set of standard,
read-only shell commands to gather CPU / RAM / disk usage, uptime, the top
running processes, listening ports and network counters. Each piece is parsed
defensively — a failure in one command degrades that field to None/empty rather
than failing the whole collection. No decrypted secret is ever logged.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from services.ssh_service import SSHConnectionParams, open_ssh_client

logger = logging.getLogger("ai_infra.metrics")

# Read-only commands. Kept POSIX-ish and resilient across common distros.
_CMDS = {
    "cpu": "top -bn1 | grep -i '%Cpu' | head -1",
    "mem": "free -b | awk '/^Mem:/ {print $2, $3}'",
    "disk": "df -P / | awk 'NR==2 {print $5}'",
    "uptime": "uptime -p 2>/dev/null || cat /proc/uptime",
    "procs": "ps -eo comm,pid,pcpu,pmem,stat --sort=-pcpu 2>/dev/null | head -n 16",
    "ports": "ss -tlnH 2>/dev/null || ss -tln 2>/dev/null",
    "net": "cat /proc/net/dev",
}


@dataclass
class CollectedMetrics:
    cpu_usage: float | None = None
    ram_usage: float | None = None
    disk_usage: float | None = None
    uptime: str | None = None
    running_processes: list[dict[str, Any]] | None = None
    open_ports: list[dict[str, Any]] | None = None
    network_stats: dict[str, Any] | None = None


def _run(client, cmd: str, timeout: int = 15) -> str:
    _, stdout, _ = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()


def _parse_cpu(out: str) -> float | None:
    # Example: "%Cpu(s):  3.2 us,  0.5 sy, ...,  95.0 id, ..."
    try:
        parts = out.split(",")
        for p in parts:
            if "id" in p:
                idle = float("".join(c for c in p if (c.isdigit() or c == ".")))
                return round(max(0.0, min(100.0, 100.0 - idle)), 1)
    except (ValueError, ZeroDivisionError):
        return None
    return None


def _parse_mem(out: str) -> float | None:
    try:
        total_s, used_s = out.split()
        total, used = float(total_s), float(used_s)
        return round(used / total * 100, 1) if total > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def _parse_disk(out: str) -> float | None:
    try:
        return float(out.replace("%", "").strip())
    except ValueError:
        return None


def _parse_procs(out: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = out.splitlines()
    for line in lines[1:]:  # skip header
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        comm, pid, pcpu, pmem, stat = parts
        rows.append({
            "name": comm,
            "pid": int(pid) if pid.isdigit() else pid,
            "cpu": _to_float(pcpu),
            "memory": _to_float(pmem),
            "status": stat,
        })
    return rows


def _parse_ports(out: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        # ss -tlnH columns: State Recv-Q Send-Q Local:Port Peer Process
        if parts[0].lower() in {"state"}:
            continue
        local = parts[3]
        port = local.rsplit(":", 1)[-1] if ":" in local else local
        proc = parts[-1] if len(parts) >= 6 and "users:" in parts[-1] else ""
        service = ""
        if "users:" in proc:
            try:
                service = proc.split('"')[1]
            except IndexError:
                service = ""
        rows.append({
            "port": int(port) if port.isdigit() else port,
            "protocol": "tcp",
            "service": service,
            "state": "LISTEN",
            "process": service,
        })
    return rows


def _parse_net(out: str) -> dict[str, Any]:
    rx = tx = 0
    for line in out.splitlines():
        if ":" not in line:
            continue
        iface, rest = line.split(":", 1)
        iface = iface.strip()
        if iface == "lo":
            continue
        cols = rest.split()
        if len(cols) >= 9:
            try:
                rx += int(cols[0])
                tx += int(cols[8])
            except ValueError:
                continue
    return {"rx_bytes": rx, "tx_bytes": tx}


def _to_float(v: str) -> float | None:
    try:
        return float(v)
    except ValueError:
        return None


def _collect_blocking(params: SSHConnectionParams) -> CollectedMetrics:
    m = CollectedMetrics()
    with open_ssh_client(params) as client:
        try:
            m.cpu_usage = _parse_cpu(_run(client, _CMDS["cpu"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("cpu collection failed: %s", type(exc).__name__)
        try:
            m.ram_usage = _parse_mem(_run(client, _CMDS["mem"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("mem collection failed: %s", type(exc).__name__)
        try:
            m.disk_usage = _parse_disk(_run(client, _CMDS["disk"]))
        except Exception:  # noqa: BLE001
            pass
        try:
            m.uptime = _run(client, _CMDS["uptime"]) or None
        except Exception:  # noqa: BLE001
            pass
        try:
            m.running_processes = _parse_procs(_run(client, _CMDS["procs"]))
        except Exception:  # noqa: BLE001
            m.running_processes = []
        try:
            m.open_ports = _parse_ports(_run(client, _CMDS["ports"]))
        except Exception:  # noqa: BLE001
            m.open_ports = []
        try:
            m.network_stats = _parse_net(_run(client, _CMDS["net"]))
        except Exception:  # noqa: BLE001
            m.network_stats = {}
    return m


async def collect_metrics(params: SSHConnectionParams) -> CollectedMetrics:
    """Async wrapper — runs the blocking SSH collection in a worker thread."""
    return await asyncio.to_thread(_collect_blocking, params)

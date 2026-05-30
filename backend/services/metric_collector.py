"""
SSH-based metric collection.

``collect_all_metrics(db, server_id)`` retrieves the server, decrypts its SSH
credentials, opens a single Paramiko connection, runs a fixed set of read-only
commands (each with a 10s timeout), parses the output into clean dictionaries,
and closes the connection. A failing/empty command degrades that field to
``None`` and collection continues. Decrypted credentials are never logged.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.server import Server
from services.ssh_service import SSHConnectionParams, open_ssh_client
from utils.encryption import EncryptionError, decrypt

logger = logging.getLogger("ai_infra.metric_collector")

PER_COMMAND_TIMEOUT = 10  # seconds; a slow command cannot block the whole run

# Exact commands as specified.
COMMANDS = {
    "cpu": 'top -bn1 | grep "Cpu(s)" | awk \'{print $2}\' | cut -d. -f1',
    "ram": "free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2}'",
    "disk": "df -h | awk 'NR>1 {print $1, $2, $3, $4, $5, $6}'",
    "uptime": "uptime -p",
    "processes": "ps aux --no-headers | awk '{print $1, $2, $3, $4, $11}' | head -50",
    "ports": "ss -tlnp | awk 'NR>1 {print $1, $4, $6}'",
    "network": "cat /proc/net/dev | awk 'NR>2 {print $1, $2, $10}'",
    "users": "who | awk '{print $1, $2, $3, $4}'",
    "failed_logins": 'lastb -n 20 2>/dev/null | head -20 || echo "no_data"',
    "loadavg": "cat /proc/loadavg",
    "kernel": "uname -r",
    "os": 'cat /etc/os-release | grep -E "^NAME|^VERSION=" | tr -d \'"\'',
}


def _run(client, cmd: str) -> str | None:
    """Run one command with a hard per-command timeout. None on failure/empty."""
    try:
        _, stdout, _ = client.exec_command(cmd, timeout=PER_COMMAND_TIMEOUT)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        return out or None
    except Exception as exc:  # noqa: BLE001 - one command failing must not abort
        logger.warning("metric command failed (%s): %s", cmd.split()[0], type(exc).__name__)
        return None


def _to_float(v: str) -> float | None:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _parse_cpu(out: str | None) -> float | None:
    if not out:
        return None
    return _to_float(out.splitlines()[0].strip())


def _parse_disk(out: str | None) -> list[dict] | None:
    if not out or out == "no_data":
        return None
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        rows.append({
            "filesystem": parts[0], "size": parts[1], "used": parts[2],
            "avail": parts[3], "use_percent": parts[4], "mount": parts[5],
        })
    return rows or None


def _root_disk_percent(disk_rows: list[dict] | None) -> float | None:
    if not disk_rows:
        return None
    root = next((d for d in disk_rows if d.get("mount") == "/"), None)
    target = root or disk_rows[0]
    return _to_float(target.get("use_percent", "").replace("%", ""))


def _parse_processes(out: str | None) -> list[dict] | None:
    if not out:
        return None
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        user, pid, cpu, mem, command = parts
        rows.append({
            "user": user,
            "pid": int(pid) if pid.isdigit() else pid,
            "cpu": _to_float(cpu),
            "memory": _to_float(mem),
            "name": command,
            "status": "running",
        })
    return rows or None


def _parse_ports(out: str | None) -> list[dict] | None:
    if not out:
        return None
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        state = parts[0]
        local = parts[1]
        process = parts[2] if len(parts) > 2 else ""
        port = local.rsplit(":", 1)[-1] if ":" in local else local
        service = ""
        if 'users:' in process or '"' in process:
            try:
                service = process.split('"')[1]
            except IndexError:
                service = ""
        rows.append({
            "port": int(port) if port.isdigit() else port,
            "protocol": "tcp",
            "service": service,
            "state": state,
            "local_address": local,
            "process": service,
        })
    return rows or None


def _parse_network(out: str | None) -> list[dict] | None:
    if not out:
        return None
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        iface = parts[0].rstrip(":")
        rows.append({
            "interface": iface,
            "rx_bytes": int(parts[1]) if parts[1].isdigit() else None,
            "tx_bytes": int(parts[2]) if parts[2].isdigit() else None,
        })
    return rows or None


def _parse_lines(out: str | None) -> list[str] | None:
    if not out or out == "no_data":
        return None
    return [ln for ln in out.splitlines() if ln.strip()] or None


def _parse_os(out: str | None) -> dict | None:
    if not out:
        return None
    info = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            info[k.strip()] = v.strip()
    return info or None


def _collect_blocking(params: SSHConnectionParams) -> dict:
    """Open one SSH session, run every command, parse, and return the dict."""
    data: dict = {}
    with open_ssh_client(params) as client:
        raw = {key: _run(client, cmd) for key, cmd in COMMANDS.items()}

    disk_rows = _parse_disk(raw.get("disk"))
    data["cpu_usage"] = _parse_cpu(raw.get("cpu"))
    data["ram_usage"] = _to_float(raw.get("ram")) if raw.get("ram") else None
    data["disk_usage"] = _root_disk_percent(disk_rows)
    data["disk_per_mount"] = disk_rows
    data["uptime"] = raw.get("uptime")
    data["running_processes"] = _parse_processes(raw.get("processes"))
    data["open_ports"] = _parse_ports(raw.get("ports"))
    data["network_stats"] = _parse_network(raw.get("network"))
    data["logged_in_users"] = _parse_lines(raw.get("users"))
    data["failed_logins"] = _parse_lines(raw.get("failed_logins"))
    data["load_average"] = raw.get("loadavg")
    data["kernel_version"] = raw.get("kernel")
    data["os_info"] = _parse_os(raw.get("os"))
    return data


async def collect_all_metrics(db: AsyncSession, server_id: uuid.UUID | str) -> dict:
    """Retrieve server, decrypt creds, collect metrics over SSH, return dict."""
    server = (
        await db.execute(select(Server).where(Server.id == server_id))
    ).scalar_one_or_none()
    if server is None:
        raise ValueError("Server not found")

    password = key = None
    try:
        if server.encrypted_ssh_password:
            password = decrypt(server.encrypted_ssh_password)
        if server.encrypted_ssh_key:
            key = decrypt(server.encrypted_ssh_key)
    except EncryptionError as exc:
        raise RuntimeError("Failed to decrypt SSH credentials") from exc

    params = SSHConnectionParams(
        host=server.ip_address,
        port=server.ssh_port,
        username=server.ssh_username,
        auth_method=server.ssh_auth_method,
        password=password,
        private_key=key,
        key_only_mode=server.ssh_key_only_mode,
    )

    # SSH work runs in a worker thread (Paramiko is blocking).
    data = await asyncio.to_thread(_collect_blocking, params)
    data["server_ip"] = server.ip_address
    data["server_id"] = str(server.id)
    return data

"""
IP allow-list enforcement for SSH connection attempts.

Before any SSH connection to a registered server, the requesting client's IP is
checked against that server's ``allowed_ip_whitelist`` (comma-separated IPs/CIDRs).
If the list is empty, the default allowed set is the dashboard server's own IP
(plus loopback). A rejected attempt returns HTTP 403 and is written to
``audit_logs``.
"""
from __future__ import annotations

import ipaddress
import socket
import uuid
from functools import lru_cache

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.server import Server
from services.audit_service import record_event

WHITELIST_DENIED_EVENT = "ip_whitelist_denied"


@lru_cache(maxsize=1)
def dashboard_default_ips() -> frozenset[str]:
    """Default allow-list: loopback + the dashboard host's own resolvable IPs."""
    ips: set[str] = {"127.0.0.1", "::1"}
    if settings.BACKEND_HOST:
        ips.add(settings.BACKEND_HOST)
    try:
        hostname = socket.gethostname()
        ips.add(socket.gethostbyname(hostname))
        for info in socket.getaddrinfo(hostname, None):
            ips.add(info[4][0])
    except OSError:
        pass
    return frozenset(ips)


def _ip_matches(client_ip: str, entry: str) -> bool:
    try:
        addr = ipaddress.ip_address(client_ip)
        if "/" in entry:
            return addr in ipaddress.ip_network(entry, strict=False)
        return addr == ipaddress.ip_address(entry)
    except ValueError:
        return False


def is_ip_allowed(server: Server, client_ip: str) -> bool:
    """True if client_ip is permitted to drive SSH connections to ``server``."""
    # The dashboard server itself is always allowed (it initiates the SSH calls).
    if client_ip in dashboard_default_ips():
        return True

    whitelist = (server.allowed_ip_whitelist or "").strip()
    if not whitelist:
        # No explicit list → only the dashboard's own IPs (checked above).
        return False

    return any(
        _ip_matches(client_ip, entry.strip())
        for entry in whitelist.split(",")
        if entry.strip()
    )


async def enforce_ip_whitelist(
    db: AsyncSession,
    server: Server,
    request: Request,
    *,
    user_id: uuid.UUID | str | None,
) -> str:
    """
    Verify the request originates from an allowed IP for this server.
    Returns the client IP on success; raises 403 (and audits) on denial.
    """
    client_ip = request.client.host if request.client else "unknown"
    if is_ip_allowed(server, client_ip):
        return client_ip

    await record_event(
        db,
        event_type=WHITELIST_DENIED_EVENT,
        success=False,
        user_id=user_id,
        ip_address=client_ip,
        target_server_id=server.id,
        description=(
            f"Blocked SSH connection: client IP {client_ip} is not in the allow-list "
            f"for server {server.name} ({server.ip_address})."
        ),
    )
    await db.commit()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Your IP address is not allowed to initiate connections to this server.",
    )

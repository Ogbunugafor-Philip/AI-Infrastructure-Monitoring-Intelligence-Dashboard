"""
In-memory registry of active SSH connections, keyed by server_id.

Privileged action execution registers its Paramiko client here for the duration
of a command so the emergency kill switch can force-close any active connection
to a server. Connections are normally short-lived and closed via try/finally;
this registry is the best-effort hook for forced termination.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_active: dict[str, set] = {}


def register(server_id: str, client) -> None:
    with _lock:
        _active.setdefault(str(server_id), set()).add(client)


def unregister(server_id: str, client) -> None:
    with _lock:
        conns = _active.get(str(server_id))
        if conns:
            conns.discard(client)
            if not conns:
                _active.pop(str(server_id), None)


def close_all(server_id: str) -> int:
    """Force-close every tracked connection to a server. Returns how many."""
    with _lock:
        conns = list(_active.get(str(server_id), set()))
        _active.pop(str(server_id), None)
    closed = 0
    for client in conns:
        try:
            client.close()
            closed += 1
        except Exception:  # noqa: BLE001
            pass
    return closed

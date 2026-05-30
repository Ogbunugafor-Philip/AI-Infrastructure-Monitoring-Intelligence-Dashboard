"""
Execute a whitelisted command on a server over SSH.

The caller passes the EXACT command string already looked up from the hardcoded
whitelist (never user input). The SSH connection is opened, the command is run,
stdout+stderr are captured, and the connection is ALWAYS closed via try/finally
(inside ``open_ssh_client``). The active connection is registered so the
emergency kill switch can force-close it.
"""
from __future__ import annotations

import asyncio
import logging

from services import connection_registry
from services.ssh_service import build_params_from_server, open_ssh_client

logger = logging.getLogger("ai_infra.action_executor")

COMMAND_TIMEOUT = 30  # seconds


def _run_blocking(params, command_string: str, server_id: str) -> str:
    with open_ssh_client(params) as client:
        connection_registry.register(server_id, client)
        try:
            _, stdout, stderr = client.exec_command(command_string, timeout=COMMAND_TIMEOUT)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
        finally:
            connection_registry.unregister(server_id, client)
    combined = out
    if err.strip():
        combined += ("\n" if combined else "") + "[stderr]\n" + err
    return combined.strip() or "(no output)"


async def execute_command(server, command_string: str) -> str:
    """Run ``command_string`` on ``server`` over SSH; return combined output.

    The command string MUST already come from the whitelist. Decrypted creds
    live only inside the worker thread and are never logged.
    """
    params = build_params_from_server(server)
    return await asyncio.to_thread(_run_blocking, params, command_string, str(server.id))

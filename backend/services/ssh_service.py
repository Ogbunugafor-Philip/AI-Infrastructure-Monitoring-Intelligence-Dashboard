"""
SSH connection testing via Paramiko.

``test_connection`` attempts to open an SSH session using either password or key
authentication and returns a (success, message) result. It honours:
  * SSH_CONNECTION_TIMEOUT  - per-attempt socket/auth timeout (.env)
  * SSH_MAX_RETRY_LIMIT     - number of retry attempts on failure (.env)
  * ssh_key_only_mode       - if set, password auth is rejected outright

For key auth, the (already-decrypted) private key is written to a temporary file
with 0600 permissions, used, and then ALWAYS deleted in a finally block — even
if the attempt raises. Decrypted secrets are never logged.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import socket
import stat
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass

import paramiko

from config import settings
from models.enums import SSHAuthMethod

logger = logging.getLogger("ai_infra.ssh")


@dataclass
class SSHConnectionParams:
    host: str
    port: int
    username: str
    auth_method: SSHAuthMethod
    password: str | None = None          # decrypted, in-memory only
    private_key: str | None = None       # decrypted PEM, in-memory only
    key_only_mode: bool = False


class ConnectionResult:
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message


def _write_temp_key(pem: str) -> str:
    """Write a private key to a 0600 temp file and return its path."""
    fd, path = tempfile.mkstemp(prefix="aimon_key_", suffix=".pem")
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)  # 0600 before writing
        with os.fdopen(fd, "w") as fh:
            fh.write(pem)
    except Exception:
        # If writing fails, make sure we don't leak the temp file.
        try:
            os.remove(path)
        except OSError:
            pass
        raise
    return path


def _attempt_once(params: SSHConnectionParams, key_path: str | None) -> None:
    """Single blocking connection attempt. Raises on failure."""
    client = paramiko.SSHClient()
    # Accept previously-unseen host keys (servers are registered ad hoc here).
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = dict(
            hostname=params.host,
            port=params.port,
            username=params.username,
            timeout=settings.SSH_CONNECTION_TIMEOUT,
            banner_timeout=settings.SSH_CONNECTION_TIMEOUT,
            auth_timeout=settings.SSH_CONNECTION_TIMEOUT,
            look_for_keys=False,   # never fall back to local user keys
            allow_agent=False,     # never use a local SSH agent
        )
        if params.auth_method == SSHAuthMethod.password:
            connect_kwargs["password"] = params.password
        else:
            connect_kwargs["key_filename"] = key_path
        client.connect(**connect_kwargs)
        # Prove the channel works.
        client.get_transport().send_ignore()
    finally:
        client.close()


def _run_test(params: SSHConnectionParams) -> ConnectionResult:
    """Blocking implementation with retry logic; safe for asyncio.to_thread."""
    # Enforce key-only mode: reject password auth immediately.
    if params.key_only_mode and params.auth_method == SSHAuthMethod.password:
        return ConnectionResult(
            False,
            "Password authentication is disabled for this server (key-only mode).",
        )

    key_path: str | None = None
    try:
        if params.auth_method == SSHAuthMethod.key:
            if not params.private_key:
                return ConnectionResult(False, "No SSH key available for key auth.")
            key_path = _write_temp_key(params.private_key)

        attempts = max(1, settings.SSH_MAX_RETRY_LIMIT)
        last_error = "unknown error"
        for i in range(attempts):
            try:
                _attempt_once(params, key_path)
                return ConnectionResult(
                    True,
                    f"Connection succeeded to {params.host}:{params.port} "
                    f"as {params.username} using {params.auth_method.value} auth.",
                )
            except paramiko.AuthenticationException:
                # Auth failures will not improve on retry — stop early.
                return ConnectionResult(
                    False, "Authentication failed: invalid credentials."
                )
            except (paramiko.SSHException, socket.error, OSError) as exc:
                last_error = type(exc).__name__
                logger.warning(
                    "SSH attempt %d/%d to %s failed: %s",
                    i + 1, attempts, params.host, last_error,
                )
        return ConnectionResult(
            False,
            f"Connection failed after {attempts} attempt(s) ({last_error}).",
        )
    finally:
        # ALWAYS remove the temp key, even on exception.
        if key_path:
            try:
                os.remove(key_path)
            except OSError:
                pass


async def test_connection(params: SSHConnectionParams) -> ConnectionResult:
    """Async wrapper — runs the blocking Paramiko logic in a worker thread."""
    return await asyncio.to_thread(_run_test, params)


@contextlib.contextmanager
def open_ssh_client(params: SSHConnectionParams) -> Iterator[paramiko.SSHClient]:
    """
    Yield a connected Paramiko client (blocking). Honours key-only mode, writes
    key material to a 0600 temp file, and ALWAYS closes the client and removes
    the temp key on exit — even if the body raises.
    """
    if params.key_only_mode and params.auth_method == SSHAuthMethod.password:
        raise PermissionError("Password authentication is disabled (key-only mode).")

    key_path: str | None = None
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        connect_kwargs = dict(
            hostname=params.host,
            port=params.port,
            username=params.username,
            timeout=settings.SSH_CONNECTION_TIMEOUT,
            banner_timeout=settings.SSH_CONNECTION_TIMEOUT,
            auth_timeout=settings.SSH_CONNECTION_TIMEOUT,
            look_for_keys=False,
            allow_agent=False,
        )
        if params.auth_method == SSHAuthMethod.password:
            connect_kwargs["password"] = params.password
        else:
            if not params.private_key:
                raise ValueError("No SSH key available for key auth.")
            key_path = _write_temp_key(params.private_key)
            connect_kwargs["key_filename"] = key_path
        client.connect(**connect_kwargs)
        yield client
    finally:
        client.close()
        if key_path:
            try:
                os.remove(key_path)
            except OSError:
                pass

"""
Server registration & management router.

Endpoints (under /api/v1/servers):
  POST   /register                      - register a new server (admin+)
  POST   /test-connection               - test SSH connectivity (admin+)
  GET    /                              - list servers (any authenticated)
  GET    /{server_id}                   - get one server (any authenticated)
  PUT    /{server_id}                   - update a server (admin+)
  DELETE /{server_id}                   - delete a server (admin+)
  POST   /{server_id}/toggle-key-only   - toggle key-only mode (admin+)
  POST   /{server_id}/reveal-credentials- reveal a decrypted credential (super_admin)

Security:
  * RBAC enforced per-endpoint (viewers get 403 on all writes/actions).
  * SSH passwords & keys are AES-256-GCM encrypted before storage and never
    returned in responses (masked) except via /reveal-credentials.
  * Every connection attempt and registration is written to audit_logs.
  * IP allow-list is enforced before SSH attempts on existing servers.
  * Email alerts on successful registration and on >=3 consecutive failures.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from middleware.ip_whitelist import enforce_ip_whitelist
from middleware.rbac import require_admin, require_super_admin, require_viewer
from models.audit_log import AuditLog
from models.enums import ActionStatus, ServerStatus, SSHAuthMethod
from models.pending_action import PendingAction
from models.server import Server
from models.user import User
from schemas.action import EmergencyKillResponse, PasswordBody
from services import action_email_service, connection_registry
from schemas.server import (
    MessageResponse,
    RevealCredentialsRequest,
    RevealCredentialsResponse,
    ServerCreate,
    ServerOut,
    ServerUpdate,
    TestConnectionRequest,
    TestConnectionResponse,
)
from services import audit_service
from services.email_service import send_email
from services.ssh_service import SSHConnectionParams, test_connection
from utils.encryption import EncryptionError, decrypt, encrypt
from utils.security import verify_password

router = APIRouter(prefix="/api/v1/servers", tags=["servers"])

SSH_ATTEMPT_EVENT = "ssh_connection_attempt"
SERVER_REGISTERED_EVENT = "server_registered"
SERVER_UPDATED_EVENT = "server_updated"
SERVER_DELETED_EVENT = "server_deleted"
KEY_ONLY_TOGGLE_EVENT = "server_key_only_toggled"
REVEAL_EVENT = "credential_reveal"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def _get_server_or_404(db: AsyncSession, server_id: uuid.UUID) -> Server:
    server = (
        await db.execute(select(Server).where(Server.id == server_id))
    ).scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return server


async def _count_consecutive_failures(db: AsyncSession, server_id: uuid.UUID) -> int:
    """Count the run of most-recent consecutive failed SSH attempts for a server."""
    rows = (
        await db.execute(
            select(AuditLog.success)
            .where(
                AuditLog.event_type == SSH_ATTEMPT_EVENT,
                AuditLog.target_server_id == server_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(25)
        )
    ).scalars().all()
    count = 0
    for ok in rows:
        if ok:
            break
        count += 1
    return count


# --------------------------------------------------------------------------- #
# Register                                                                     #
# --------------------------------------------------------------------------- #
@router.post("/register", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
async def register_server(
    request: Request,
    payload: ServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ServerOut:
    ip = _client_ip(request)

    # Defense-in-depth: re-assert the auth/credential invariants in the handler.
    if payload.ssh_auth_method == SSHAuthMethod.password:
        if payload.ssh_key_only_mode:
            raise HTTPException(status_code=422, detail="key-only mode forbids password auth")
        if not payload.ssh_password:
            raise HTTPException(status_code=422, detail="ssh_password required for password auth")
    elif payload.ssh_auth_method == SSHAuthMethod.key and not payload.ssh_key:
        raise HTTPException(status_code=422, detail="ssh_key required for key auth")

    server = Server(
        name=payload.name,
        ip_address=payload.ip_address,
        ssh_port=payload.ssh_port,
        ssh_username=payload.ssh_username,
        ssh_auth_method=payload.ssh_auth_method,
        # Encrypt credentials at rest — never store plaintext.
        encrypted_ssh_password=encrypt(payload.ssh_password) if payload.ssh_password else None,
        encrypted_ssh_key=encrypt(payload.ssh_key) if payload.ssh_key else None,
        ssh_key_only_mode=payload.ssh_key_only_mode,
        allowed_ip_whitelist=payload.allowed_ip_whitelist,
        created_by=current_user.id,
    )
    db.add(server)
    await db.flush()

    await audit_service.record_event(
        db,
        event_type=SERVER_REGISTERED_EVENT,
        success=True,
        user_id=current_user.id,
        ip_address=ip,
        target_server_id=server.id,
        description=f"Server '{server.name}' registered with IP {server.ip_address}.",
    )
    await db.commit()
    await db.refresh(server)

    # Notify operators of the new server registration.
    await send_email(
        subject="[AI Infra Monitoring] New server registered",
        body=(
            "A new server was registered on the AI Infrastructure Monitoring Dashboard.\n\n"
            f"Name: {server.name}\n"
            f"IP address: {server.ip_address}\n"
            f"Registered by: {current_user.email}\n"
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
        ),
    )
    return ServerOut.from_model(server)


# --------------------------------------------------------------------------- #
# Test connection                                                             #
# --------------------------------------------------------------------------- #
@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_server_connection(
    request: Request,
    payload: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> TestConnectionResponse:
    ip = _client_ip(request)
    server: Server | None = None

    if payload.server_id is not None:
        server = await _get_server_or_404(db, payload.server_id)
        # Enforce the per-server IP allow-list before any SSH attempt.
        await enforce_ip_whitelist(db, server, request, user_id=current_user.id)

        auth_method = server.ssh_auth_method
        key_only = server.ssh_key_only_mode
        host, port, username = server.ip_address, server.ssh_port, server.ssh_username
        password = key = None
        try:
            if server.encrypted_ssh_password:
                password = decrypt(server.encrypted_ssh_password)
            if server.encrypted_ssh_key:
                key = decrypt(server.encrypted_ssh_key)
        except EncryptionError:
            raise HTTPException(status_code=500, detail="Stored credential could not be decrypted")
    else:
        # Inline (pre-registration) test using submitted values.
        auth_method = payload.ssh_auth_method
        key_only = payload.ssh_key_only_mode
        host, port, username = payload.ip_address, payload.ssh_port or 22, payload.ssh_username
        password, key = payload.ssh_password, payload.ssh_key

    # Key-only enforcement (also enforced inside ssh_service as defense-in-depth).
    if key_only and auth_method == SSHAuthMethod.password:
        result_success, result_message = False, "Password auth is disabled (key-only mode)."
    else:
        result = await test_connection(
            SSHConnectionParams(
                host=host, port=port, username=username, auth_method=auth_method,
                password=password, private_key=key, key_only_mode=key_only,
            )
        )
        result_success, result_message = result.success, result.message

    await audit_service.record_event(
        db,
        event_type=SSH_ATTEMPT_EVENT,
        success=result_success,
        user_id=current_user.id,
        ip_address=ip,
        target_server_id=server.id if server else None,
        description=(
            f"SSH connection attempt to {host}:{port} using {auth_method.value} auth "
            f"- {'success' if result_success else 'failure'}."
        ),
    )
    await db.commit()

    # Alert on repeated consecutive failures for a registered server.
    if server is not None and not result_success:
        consecutive = await _count_consecutive_failures(db, server.id)
        if consecutive >= 3:
            await send_email(
                subject="[AI Infra Monitoring] Repeated SSH connection failures",
                body=(
                    "Multiple consecutive SSH connection failures detected.\n\n"
                    f"Server: {server.name} ({server.ip_address})\n"
                    f"Consecutive failed attempts: {consecutive}\n"
                    f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
                ),
            )

    return TestConnectionResponse(success=result_success, message=result_message)


# --------------------------------------------------------------------------- #
# List / get                                                                  #
# --------------------------------------------------------------------------- #
@router.get("/", response_model=list[ServerOut])
async def list_servers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> list[ServerOut]:
    servers = (
        await db.execute(select(Server).order_by(Server.created_at.desc()))
    ).scalars().all()
    return [ServerOut.from_model(s) for s in servers]


@router.get("/{server_id}", response_model=ServerOut)
async def get_server(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> ServerOut:
    server = await _get_server_or_404(db, server_id)
    return ServerOut.from_model(server)


# --------------------------------------------------------------------------- #
# Update                                                                       #
# --------------------------------------------------------------------------- #
@router.put("/{server_id}", response_model=ServerOut)
async def update_server(
    request: Request,
    server_id: uuid.UUID,
    payload: ServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ServerOut:
    server = await _get_server_or_404(db, server_id)
    data = payload.model_dump(exclude_unset=True)

    # Re-encrypt any supplied credentials; never store plaintext.
    if "ssh_password" in data:
        pwd = data.pop("ssh_password")
        server.encrypted_ssh_password = encrypt(pwd) if pwd else None
    if "ssh_key" in data:
        key = data.pop("ssh_key")
        server.encrypted_ssh_key = encrypt(key) if key else None

    for field, value in data.items():
        setattr(server, field, value)

    # Consistency: key-only mode must not coexist with password auth.
    if server.ssh_key_only_mode and server.ssh_auth_method == SSHAuthMethod.password:
        raise HTTPException(status_code=422, detail="key-only mode forbids password auth method")

    await audit_service.record_event(
        db,
        event_type=SERVER_UPDATED_EVENT,
        success=True,
        user_id=current_user.id,
        ip_address=_client_ip(request),
        target_server_id=server.id,
        description=f"Server '{server.name}' updated (fields: {', '.join(data) or 'credentials'}).",
    )
    await db.commit()
    await db.refresh(server)
    return ServerOut.from_model(server)


# --------------------------------------------------------------------------- #
# Delete                                                                       #
# --------------------------------------------------------------------------- #
@router.delete("/{server_id}", response_model=MessageResponse)
async def delete_server(
    request: Request,
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> MessageResponse:
    server = await _get_server_or_404(db, server_id)
    name, sip = server.name, server.ip_address
    await db.delete(server)
    await audit_service.record_event(
        db,
        event_type=SERVER_DELETED_EVENT,
        success=True,
        user_id=current_user.id,
        ip_address=_client_ip(request),
        target_server_id=None,  # row is being removed
        description=f"Server '{name}' ({sip}) deleted.",
    )
    await db.commit()
    return MessageResponse(message=f"Server '{name}' deleted")


# --------------------------------------------------------------------------- #
# Toggle key-only mode                                                         #
# --------------------------------------------------------------------------- #
@router.post("/{server_id}/toggle-key-only", response_model=ServerOut)
async def toggle_key_only(
    request: Request,
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ServerOut:
    server = await _get_server_or_404(db, server_id)
    new_state = not server.ssh_key_only_mode

    # If enabling key-only on a password-auth server, require a key to exist.
    if new_state and server.ssh_auth_method == SSHAuthMethod.password and not server.encrypted_ssh_key:
        raise HTTPException(
            status_code=422,
            detail="Cannot enable key-only mode: server has no SSH key configured.",
        )

    server.ssh_key_only_mode = new_state
    await audit_service.record_event(
        db,
        event_type=KEY_ONLY_TOGGLE_EVENT,
        success=True,
        user_id=current_user.id,
        ip_address=_client_ip(request),
        target_server_id=server.id,
        description=(
            f"Key-only mode {'ENABLED' if new_state else 'DISABLED'} for server "
            f"'{server.name}' by {current_user.email}."
        ),
    )
    await db.commit()
    await db.refresh(server)
    return ServerOut.from_model(server)


# --------------------------------------------------------------------------- #
# Reveal credentials (super_admin + password re-verification)                  #
# --------------------------------------------------------------------------- #
@router.post("/{server_id}/reveal-credentials", response_model=RevealCredentialsResponse)
async def reveal_credentials(
    request: Request,
    server_id: uuid.UUID,
    payload: RevealCredentialsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),
) -> RevealCredentialsResponse:
    ip = _client_ip(request)
    server = await _get_server_or_404(db, server_id)

    # Re-verify the caller's own dashboard password before revealing anything.
    if not verify_password(payload.dashboard_password, current_user.hashed_password):
        await audit_service.record_event(
            db,
            event_type=REVEAL_EVENT,
            success=False,
            user_id=current_user.id,
            ip_address=ip,
            target_server_id=server.id,
            description="Failed credential reveal: dashboard password verification failed.",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password verification failed",
        )

    try:
        if server.ssh_auth_method == SSHAuthMethod.password:
            if not server.encrypted_ssh_password:
                raise HTTPException(status_code=404, detail="No password credential stored")
            credential = decrypt(server.encrypted_ssh_password)
        else:
            if not server.encrypted_ssh_key:
                raise HTTPException(status_code=404, detail="No key credential stored")
            credential = decrypt(server.encrypted_ssh_key)
    except EncryptionError:
        raise HTTPException(status_code=500, detail="Stored credential could not be decrypted")

    await audit_service.record_event(
        db,
        event_type=REVEAL_EVENT,
        success=True,
        user_id=current_user.id,
        ip_address=ip,
        target_server_id=server.id,
        description=(
            f"Credential revealed for server '{server.name}' "
            f"({server.ssh_auth_method.value}) by {current_user.email}."
        ),
    )
    await db.commit()
    return RevealCredentialsResponse(auth_method=server.ssh_auth_method, credential=credential)


EMERGENCY_KILL_EVENT = "emergency_kill"


@router.post("/{server_id}/emergency-kill", response_model=EmergencyKillResponse)
async def emergency_kill(
    request: Request,
    server_id: uuid.UUID,
    payload: PasswordBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_super_admin),  # super_admin only
) -> EmergencyKillResponse:
    """
    Emergency kill switch — irreversibly revokes a server's stored SSH
    credentials, marks it offline, cancels its pending/approved actions, and
    force-closes any tracked SSH connections. Requires password re-verification.
    """
    ip = _client_ip(request)
    server = await _get_server_or_404(db, server_id)

    if not verify_password(payload.dashboard_password, current_user.hashed_password):
        await audit_service.record_event(
            db, event_type=EMERGENCY_KILL_EVENT, success=False,
            user_id=current_user.id, ip_address=ip, target_server_id=server.id,
            description="Emergency kill rejected: password verification failed.",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password verification failed")

    # 1) Revoke credentials + mark offline.
    server.encrypted_ssh_password = None
    server.encrypted_ssh_key = None
    server.status = ServerStatus.offline

    # 2) Cancel all pending/approved actions for this server.
    cancel_result = await db.execute(
        update(PendingAction)
        .where(
            PendingAction.server_id == server.id,
            PendingAction.status.in_([
                ActionStatus.pending,
                ActionStatus.awaiting_second_confirmation,
                ActionStatus.approved,
            ]),
        )
        .values(status=ActionStatus.cancelled)
    )
    actions_cancelled = cancel_result.rowcount or 0

    # 3) Force-close any tracked SSH connections to this server.
    connections_terminated = connection_registry.close_all(str(server.id))

    await audit_service.record_event(
        db, event_type=EMERGENCY_KILL_EVENT, success=True,
        user_id=current_user.id, ip_address=ip, target_server_id=server.id,
        description=(
            f"EMERGENCY KILL on {server.name} ({server.ip_address}) by {current_user.email}: "
            f"credentials revoked, {actions_cancelled} action(s) cancelled, "
            f"{connections_terminated} connection(s) terminated."
        ),
    )
    await db.commit()

    await action_email_service.notify_emergency_kill(
        triggered_by=current_user.email, server=server, cancelled_actions=actions_cancelled,
    )

    return EmergencyKillResponse(
        server_id=server.id,
        credentials_revoked=True,
        actions_cancelled=actions_cancelled,
        connections_terminated=connections_terminated,
        status="offline",
        message="SSH credentials revoked and all pending actions cancelled. This cannot be undone.",
    )

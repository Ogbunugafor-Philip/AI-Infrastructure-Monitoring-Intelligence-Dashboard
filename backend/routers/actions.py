"""
Privileged action execution router.

Lifecycle: request -> verify-password -> (high risk: second-confirm within a
60s time lock) -> execute. Every command is the EXACT hardcoded string looked up
from the whitelist by command_key; user-supplied command strings are never run.

RBAC: viewers get 403 on every endpoint here except the read-only command
catalog. Admin+ can request/confirm/execute; an admin cannot second-confirm
their own high-risk request. Output is sanitized before storage/return and SSH
connections are always closed via try/finally inside the executor.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.rbac import require_admin, require_viewer
from models.enums import ActionStatus, RiskLevel, UserRole
from models.pending_action import PendingAction
from models.security_scan import SecurityScan
from models.server import Server
from models.user import User
from schemas.action import (
    ActionHistoryPage,
    ActionOut,
    ActionRequestBody,
    CommandCatalog,
    DryRunRequest,
    DryRunResponse,
    PasswordBody,
)
from schemas.security_scan import (
    SecurityScanHistoryItem,
    SecurityScanHistoryPage,
    SecurityScanOut,
)
from services import action_email_service, audit_service
from services.action_executor import execute_command
from services.data_sanitizer import sanitize_text
from services.vulnerability_scanner import scan_server
from utils.command_whitelist import (
    CommandNotWhitelistedError,
    get_catalog,
    get_command,
    get_risk_level,
)
from utils.security import verify_password

router = APIRouter(prefix="/api/v1/actions", tags=["actions"])

# Security-scan endpoints live under /api/v1/servers (path per spec) but are
# defined here alongside the action logic they relate to.
scan_router = APIRouter(prefix="/api/v1/servers", tags=["security-scan"])

ACTION_EXPIRY_MINUTES = 10
TIME_LOCK_SECONDS = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _get_server_or_404(db: AsyncSession, server_id) -> Server:
    server = (await db.execute(select(Server).where(Server.id == server_id))).scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


async def _get_action_or_404(db: AsyncSession, action_id) -> PendingAction:
    action = (
        await db.execute(select(PendingAction).where(PendingAction.id == action_id))
    ).scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


def _validate_key(command_key: str) -> tuple[str, str]:
    """Return (command_string, risk_level) or raise 422 if not whitelisted."""
    try:
        return get_command(command_key), get_risk_level(command_key)
    except CommandNotWhitelistedError:
        raise HTTPException(status_code=422, detail=f"Command '{command_key}' is not whitelisted")


# --------------------------------------------------------------------------- #
# Catalog (all authenticated roles)                                            #
# --------------------------------------------------------------------------- #
@router.get("/commands", response_model=CommandCatalog)
async def list_commands(current_user: User = Depends(require_viewer)) -> CommandCatalog:
    return CommandCatalog(**get_catalog())


# --------------------------------------------------------------------------- #
# Dry run (admin+) — execute & return output, store nothing permanent          #
# --------------------------------------------------------------------------- #
@router.post("/dry-run", response_model=DryRunResponse)
async def dry_run(
    request: Request,
    payload: DryRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DryRunResponse:
    command_string, _risk = _validate_key(payload.command_key)
    server = await _get_server_or_404(db, payload.server_id)

    try:
        raw_output = await execute_command(server, command_string)
    except Exception as exc:  # noqa: BLE001
        raw_output = f"[execution error: {type(exc).__name__}]"
    output = await sanitize_text(raw_output, db=db, server_id=server.id)

    await audit_service.record_event(
        db, event_type="action_dry_run", success=True,
        user_id=current_user.id, ip_address=_client_ip(request), target_server_id=server.id,
        description=f"Dry-run '{payload.command_key}' on {server.ip_address}.",
    )
    await db.commit()

    return DryRunResponse(
        server_ip=server.ip_address,
        command_key=payload.command_key,
        exact_command_string=command_string,
        output=output,
        executed_at=_now(),
    )


# --------------------------------------------------------------------------- #
# Request an action (admin+)                                                   #
# --------------------------------------------------------------------------- #
@router.post("/request", response_model=ActionOut, status_code=201)
async def request_action(
    request: Request,
    payload: ActionRequestBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ActionOut:
    command_string, risk = _validate_key(payload.command_key)
    server = await _get_server_or_404(db, payload.server_id)

    action = PendingAction(
        server_id=server.id,
        requested_by_user_id=current_user.id,
        command_key=payload.command_key,
        command_string=command_string,
        risk_level=RiskLevel(risk),
        status=ActionStatus.pending,
        second_confirmation_required=(risk == "high"),
        expires_at=_now() + timedelta(minutes=ACTION_EXPIRY_MINUTES),
    )
    db.add(action)
    await audit_service.record_event(
        db, event_type="action_requested", success=True,
        user_id=current_user.id, ip_address=_client_ip(request), target_server_id=server.id,
        description=f"Action '{payload.command_key}' ({risk}) requested on {server.ip_address}.",
    )
    await db.commit()
    await db.refresh(action)
    return ActionOut.from_model(action, server)


# --------------------------------------------------------------------------- #
# Verify password (admin+, requester only)                                     #
# --------------------------------------------------------------------------- #
@router.post("/{action_id}/verify-password", response_model=ActionOut)
async def verify_action_password(
    request: Request,
    action_id: uuid.UUID,
    payload: PasswordBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ActionOut:
    action = await _get_action_or_404(db, action_id)
    if action.requested_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the requester can verify this action")
    if action.status not in (ActionStatus.pending,):
        raise HTTPException(status_code=409, detail=f"Action is {action.status.value}")

    if not verify_password(payload.dashboard_password, current_user.hashed_password):
        await audit_service.record_event(
            db, event_type="action_password_failed", success=False,
            user_id=current_user.id, ip_address=_client_ip(request), target_server_id=action.server_id,
            description=f"Password verification failed for action {action.id}.",
        )
        await db.commit()
        raise HTTPException(status_code=403, detail="Password verification failed")

    action.password_verified = True
    if action.risk_level == RiskLevel.high:
        action.status = ActionStatus.awaiting_second_confirmation
        action.time_lock_expires_at = _now() + timedelta(seconds=TIME_LOCK_SECONDS)
    else:
        action.status = ActionStatus.approved

    await audit_service.record_event(
        db, event_type="action_password_verified", success=True,
        user_id=current_user.id, ip_address=_client_ip(request), target_server_id=action.server_id,
        description=f"Password verified for action {action.id} ({action.risk_level.value}).",
    )
    await db.commit()
    await db.refresh(action)
    server = await _get_server_or_404(db, action.server_id)
    return ActionOut.from_model(action, server)


# --------------------------------------------------------------------------- #
# Second confirmation (admin+, NOT the requester)                              #
# --------------------------------------------------------------------------- #
@router.post("/{action_id}/second-confirm", response_model=ActionOut)
async def second_confirm(
    request: Request,
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ActionOut:
    action = await _get_action_or_404(db, action_id)

    if action.requested_by_user_id == current_user.id:
        raise HTTPException(status_code=403, detail="You cannot confirm your own high risk action")
    if not action.second_confirmation_required:
        raise HTTPException(status_code=400, detail="This action does not require second confirmation")
    if action.status != ActionStatus.awaiting_second_confirmation:
        raise HTTPException(status_code=409, detail=f"Action is {action.status.value}")

    # Time-lock window check.
    if action.time_lock_expires_at and _now() > action.time_lock_expires_at:
        action.status = ActionStatus.expired
        await audit_service.record_event(
            db, event_type="action_expired", success=False,
            user_id=current_user.id, target_server_id=action.server_id,
            description=f"Action {action.id} expired before second confirmation.",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Time lock expired; action expired")

    action.confirmed_by_user_id = current_user.id
    action.second_confirmation_received = True
    action.status = ActionStatus.approved

    server = await _get_server_or_404(db, action.server_id)
    requester = (await db.execute(select(User).where(User.id == action.requested_by_user_id))).scalar_one_or_none()

    await audit_service.record_event(
        db, event_type="action_second_confirmed", success=True,
        user_id=current_user.id, ip_address=_client_ip(request), target_server_id=action.server_id,
        description=(
            f"High-risk action {action.id} ({action.command_key}) second-confirmed by "
            f"{current_user.email}; requested by {requester.email if requester else 'unknown'}."
        ),
    )
    await db.commit()
    await db.refresh(action)

    await action_email_service.notify_high_risk_approved(
        requester=requester.email if requester else "unknown",
        confirmer=current_user.email,
        server=server,
        command_string=action.command_string,
    )
    return ActionOut.from_model(action, server)


# --------------------------------------------------------------------------- #
# Cancel (admin+)                                                              #
# --------------------------------------------------------------------------- #
@router.post("/{action_id}/cancel", response_model=ActionOut)
async def cancel_action(
    request: Request,
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ActionOut:
    action = await _get_action_or_404(db, action_id)
    if action.status in (ActionStatus.completed, ActionStatus.executing, ActionStatus.cancelled, ActionStatus.expired):
        raise HTTPException(status_code=409, detail=f"Cannot cancel an action that is {action.status.value}")

    action.status = ActionStatus.cancelled
    server = await _get_server_or_404(db, action.server_id)
    await audit_service.record_event(
        db, event_type="action_cancelled", success=True,
        user_id=current_user.id, ip_address=_client_ip(request), target_server_id=action.server_id,
        description=f"Action {action.id} ({action.command_key}) cancelled by {current_user.email}.",
    )
    await db.commit()
    await db.refresh(action)
    await action_email_service.notify_action_cancelled(
        cancelled_by=current_user.email, server=server, command_string=action.command_string,
    )
    return ActionOut.from_model(action, server)


# --------------------------------------------------------------------------- #
# Execute (admin+)                                                             #
# --------------------------------------------------------------------------- #
@router.post("/{action_id}/execute", response_model=ActionOut)
async def execute_action(
    request: Request,
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ActionOut:
    action = await _get_action_or_404(db, action_id)

    # Pre-flight gating.
    if action.status != ActionStatus.approved:
        raise HTTPException(status_code=409, detail=f"Action must be approved (is {action.status.value})")
    if _now() > action.expires_at:
        action.status = ActionStatus.expired
        await db.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Action has expired")
    if not action.password_verified:
        raise HTTPException(status_code=403, detail="Password not verified")
    if action.second_confirmation_required and not action.second_confirmation_received:
        raise HTTPException(status_code=403, detail="Second confirmation required")

    action.status = ActionStatus.executing
    action.executed_at = _now()
    await db.commit()

    server = await _get_server_or_404(db, action.server_id)
    # Defense in depth: re-resolve the canonical command from the whitelist.
    command_string = get_command(action.command_key)

    try:
        raw_output = await execute_command(server, command_string)
    except Exception as exc:  # noqa: BLE001
        raw_output = f"[execution error: {type(exc).__name__}]"
    output = await sanitize_text(raw_output, db=db, server_id=server.id)

    action.execution_output = output
    action.status = ActionStatus.completed
    action.completed_at = _now()

    confirmer = None
    if action.confirmed_by_user_id:
        confirmer = (await db.execute(select(User).where(User.id == action.confirmed_by_user_id))).scalar_one_or_none()

    await audit_service.record_event(
        db, event_type="action_executed", success=True,
        user_id=action.requested_by_user_id, ip_address=_client_ip(request), target_server_id=server.id,
        description=(
            f"Executed '{action.command_key}' ({action.risk_level.value}) on {server.ip_address} | "
            f"confirmed_by={action.confirmed_by_user_id or 'n/a'} | command='{command_string}' | "
            f"output: {output[:1500]}"
        ),
    )
    await db.commit()
    await db.refresh(action)

    await action_email_service.notify_action_executed(
        triggered_by=current_user.email,
        confirmed_by=confirmer.email if confirmer else None,
        server=server,
        command_string=command_string,
        risk_level=action.risk_level.value,
        output=output,
    )
    return ActionOut.from_model(action, server)


# --------------------------------------------------------------------------- #
# Status (admin+)                                                              #
# --------------------------------------------------------------------------- #
@router.get("/{action_id}/status", response_model=ActionOut)
async def action_status(
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ActionOut:
    action = await _get_action_or_404(db, action_id)
    server = await _get_server_or_404(db, action.server_id)
    return ActionOut.from_model(action, server)


# --------------------------------------------------------------------------- #
# Awaiting MY confirmation (admin+) — high-risk actions requested by others    #
# --------------------------------------------------------------------------- #
@router.get("/awaiting-confirmation", response_model=list[ActionOut])
async def awaiting_confirmation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[ActionOut]:
    """High-risk actions awaiting a second confirmation that THIS user may give
    (i.e. requested by someone else and still within their time lock)."""
    rows = (
        await db.execute(
            select(PendingAction).where(
                PendingAction.status == ActionStatus.awaiting_second_confirmation,
                PendingAction.requested_by_user_id != current_user.id,
            ).order_by(PendingAction.created_at.desc())
        )
    ).scalars().all()
    server_ids = {r.server_id for r in rows}
    servers = {}
    if server_ids:
        for s in (await db.execute(select(Server).where(Server.id.in_(server_ids)))).scalars().all():
            servers[s.id] = s
    return [ActionOut.from_model(r, servers.get(r.server_id)) for r in rows]


# --------------------------------------------------------------------------- #
# History (admin+ ; admin sees own, super sees all)                            #
# --------------------------------------------------------------------------- #
@router.get("/history", response_model=ActionHistoryPage)
async def action_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    server_id: uuid.UUID | None = None,
    action_status_filter: ActionStatus | None = Query(None, alias="status"),
    risk_level: RiskLevel | None = None,
    user_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ActionHistoryPage:
    conds = []
    # Admin sees only their own actions; super_admin sees all.
    if current_user.role != UserRole.super_admin:
        conds.append(PendingAction.requested_by_user_id == current_user.id)
    if server_id:
        conds.append(PendingAction.server_id == server_id)
    if action_status_filter:
        conds.append(PendingAction.status == action_status_filter)
    if risk_level:
        conds.append(PendingAction.risk_level == risk_level)
    if user_id:
        conds.append(PendingAction.requested_by_user_id == user_id)
    if date_from:
        conds.append(PendingAction.created_at >= date_from)
    if date_to:
        conds.append(PendingAction.created_at <= date_to)

    total = (await db.execute(select(func.count()).select_from(PendingAction).where(*conds))).scalar_one()
    rows = (
        await db.execute(
            select(PendingAction).where(*conds)
            .order_by(PendingAction.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()

    # Map server ids -> servers for IP/name display.
    server_ids = {r.server_id for r in rows}
    servers = {}
    if server_ids:
        for s in (await db.execute(select(Server).where(Server.id.in_(server_ids)))).scalars().all():
            servers[s.id] = s

    total_pages = (total + page_size - 1) // page_size
    return ActionHistoryPage(
        items=[ActionOut.from_model(r, servers.get(r.server_id)) for r in rows],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


# --------------------------------------------------------------------------- #
# Security scan (/api/v1/servers/{server_id}/security-scan)                    #
# --------------------------------------------------------------------------- #
@scan_router.post("/{server_id}/security-scan", response_model=SecurityScanOut)
async def run_security_scan(
    request: Request,
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),  # privileged (runs SSH commands)
) -> SecurityScanOut:
    server = (await db.execute(select(Server).where(Server.id == server_id))).scalar_one_or_none()
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        result = await scan_server(db, server_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Scan failed ({type(exc).__name__})")

    scan = SecurityScan(
        server_id=server.id,
        scan_results=result["results"],
        total_checks=result["total_checks"],
        passed=result["passed"],
        warnings=result["warnings"],
        critical_findings=result["critical_findings"],
        overall_score=result["overall_score"],
        scanned_by_user_id=current_user.id,
    )
    db.add(scan)
    await audit_service.record_event(
        db, event_type="security_scan", success=True,
        user_id=current_user.id, ip_address=_client_ip(request), target_server_id=server.id,
        description=(
            f"Security scan on {server.ip_address}: score {result['overall_score']}/100, "
            f"{result['passed']} pass / {result['warnings']} warn / {result['critical_findings']} critical."
        ),
    )
    await db.commit()
    await db.refresh(scan)
    return SecurityScanOut.model_validate(scan)


@scan_router.get("/{server_id}/security-scan/latest", response_model=SecurityScanOut | None)
async def latest_security_scan(
    server_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> SecurityScanOut | None:
    scan = (
        await db.execute(
            select(SecurityScan).where(SecurityScan.server_id == server_id)
            .order_by(SecurityScan.scanned_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return SecurityScanOut.model_validate(scan) if scan else None


@scan_router.get("/{server_id}/security-scan/history", response_model=SecurityScanHistoryPage)
async def security_scan_history(
    server_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_viewer),
) -> SecurityScanHistoryPage:
    total = (
        await db.execute(
            select(func.count()).select_from(SecurityScan).where(SecurityScan.server_id == server_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(SecurityScan).where(SecurityScan.server_id == server_id)
            .order_by(SecurityScan.scanned_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return SecurityScanHistoryPage(
        items=[SecurityScanHistoryItem.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )

"""
Authentication router.

Endpoints (all under /api/v1/auth):
  POST /login    - authenticate, issue access (15 min) + refresh (7 day) tokens
  POST /refresh  - rotate the refresh token, issue a fresh access + refresh pair
  POST /logout   - revoke the supplied refresh token

Security behaviours:
  * Argon2 password verification (constant-effort; dummy-verify on unknown user
    to reduce user-enumeration timing differences).
  * Every login attempt is written to audit_logs (success or failure).
  * Refresh tokens are single-use: on /refresh the presented token is revoked
    and a new one issued (rotation). Reuse of a revoked token is rejected.
  * Failed logins feed the intrusion-detection service, which alerts by email
    and temporarily blocks an IP once the threshold is reached.
  * slowapi rate limiting is applied to every endpoint here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
import re

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from middleware.rate_limit import LOGIN_RATE_LIMIT, limiter
from middleware.rbac import get_current_user
from models.refresh_token import RefreshToken
from models.user import User
from schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordVerifyRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from services import audit_service, intrusion_detection
from utils.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# A throwaway Argon2 hash used to equalize timing when the user does not exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")

LOGIN_EVENT = "login"
LOGOUT_EVENT = "logout"
REFRESH_EVENT = "token_refresh"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _access_ttl_seconds() -> int:
    return settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    ip = _client_ip(request)

    # Block early if this IP is already past the intrusion threshold.
    if await intrusion_detection.is_ip_temporarily_blocked(db, ip):
        await audit_service.record_event(
            db, event_type=LOGIN_EVENT, success=False, ip_address=ip,
            description="Login blocked: IP temporarily locked by intrusion detection.",
        )
        await db.commit()  # persist audit before the HTTPException rolls back get_db
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts from this IP. Try again later.",
        )

    user = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()

    # Constant-effort verification regardless of whether the user exists.
    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        await _handle_failed_login(db, ip, payload.email, user=None)
        await db.commit()  # persist audit/intrusion records before raising
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.is_locked or not user.is_active:
        await audit_service.record_event(
            db, event_type=LOGIN_EVENT, success=False, user_id=user.id, ip_address=ip,
            description="Login rejected: account locked or inactive.",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked or inactive. Contact an administrator.",
        )

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        await _handle_failed_login(db, ip, payload.email, user=user)
        await db.commit()  # persist failed-attempt counter + audit before raising
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # ---- success ----
    user.failed_login_attempts = 0
    user.last_login = datetime.now(timezone.utc)
    await audit_service.record_event(
        db, event_type=LOGIN_EVENT, success=True, user_id=user.id, ip_address=ip,
        description="Successful login.",
    )
    return await _issue_token_pair(db, user)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    ip = _client_ip(request)
    token_hash = hash_token(payload.refresh_token)

    stored = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked or stored.expires_at <= now:
        # Possible token reuse/replay — record and reject.
        await audit_service.record_event(
            db, event_type=REFRESH_EVENT, success=False, ip_address=ip,
            user_id=stored.user_id if stored else None,
            description="Refresh rejected: token missing, revoked, or expired.",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = (
        await db.execute(select(User).where(User.id == stored.user_id))
    ).scalar_one_or_none()
    if user is None or not user.is_active or user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or locked",
        )

    # Rotate: revoke the presented token immediately, then issue a new pair.
    stored.revoked = True
    await db.flush()
    await audit_service.record_event(
        db, event_type=REFRESH_EVENT, success=True, user_id=user.id, ip_address=ip,
        description="Refresh token rotated.",
    )
    return await _issue_token_pair(db, user)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the authenticated user's profile (for the header / RBAC UI)."""
    return UserOut.model_validate(current_user)


_PW_RULES = (
    (lambda p: len(p) >= 8, "at least 8 characters"),
    (lambda p: bool(re.search(r"[A-Z]", p)), "an uppercase letter"),
    (lambda p: bool(re.search(r"[0-9]", p)), "a number"),
    (lambda p: bool(re.search(r"[^A-Za-z0-9]", p)), "a special character"),
)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """
    Change the authenticated user's password: verify current password, enforce
    complexity, rehash, clear force_password_change, revoke all refresh tokens,
    and audit.
    """
    ip = _client_ip(request)
    if not verify_password(payload.current_password, current_user.hashed_password):
        await audit_service.record_event(
            db, event_type="password_change", success=False, user_id=current_user.id,
            ip_address=ip, description="Password change failed: current password incorrect.",
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")

    failed = [msg for rule, msg in _PW_RULES if not rule(payload.new_password)]
    if failed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must contain " + ", ".join(failed) + ".",
        )
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(status_code=422, detail="New password must differ from the current password.")

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.force_password_change = False
    # Invalidate all existing refresh tokens for this user.
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == current_user.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    await audit_service.record_event(
        db, event_type="password_change", success=True, user_id=current_user.id, ip_address=ip,
        description="Password changed successfully; all refresh tokens revoked.",
    )
    await db.commit()
    return MessageResponse(message="Password changed successfully")


@router.post("/verify-password", response_model=MessageResponse)
async def verify_current_password(
    request: Request,
    payload: PasswordVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """
    Re-verify the authenticated user's own dashboard password.

    Used by the frontend as a confirmation gate before revealing sensitive
    fields (e.g. an SSH key being entered on the registration form).
    """
    ip = _client_ip(request)
    if not verify_password(payload.password, current_user.hashed_password):
        await audit_service.record_event(
            db, event_type="password_reverify", success=False, user_id=current_user.id,
            ip_address=ip, description="Dashboard password re-verification failed.",
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Password verification failed"
        )
    return MessageResponse(message="verified")


@router.post("/logout", response_model=MessageResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
async def logout(
    request: Request,
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    ip = _client_ip(request)
    token_hash = hash_token(payload.refresh_token)
    stored = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()

    if stored is not None and not stored.revoked:
        stored.revoked = True
        await db.flush()

    await audit_service.record_event(
        db, event_type=LOGOUT_EVENT, success=True, ip_address=ip,
        user_id=stored.user_id if stored else None,
        description="User logged out; refresh token revoked.",
    )
    return MessageResponse(message="Logged out successfully")


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #
async def _issue_token_pair(db: AsyncSession, user: User) -> TokenResponse:
    """Create an access token and a persisted (hashed) refresh token."""
    access = create_access_token(user_id=user.id, role=user.role.value)
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=refresh_token_expiry(),
            revoked=False,
        )
    )
    await db.flush()
    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=_access_ttl_seconds(),
        force_password_change=bool(user.force_password_change),
    )


async def _handle_failed_login(
    db: AsyncSession, ip: str, email: str, *, user: User | None
) -> None:
    """Record a failed login and run intrusion-detection evaluation."""
    await audit_service.record_event(
        db,
        event_type=intrusion_detection.FAILED_LOGIN_EVENT,
        success=False,
        user_id=user.id if user else None,
        ip_address=ip,
        description="Failed login attempt.",
    )
    # Triggers an email alert + audit entry once the threshold is reached.
    await intrusion_detection.evaluate_failed_login(db, ip, email_attempted=email)

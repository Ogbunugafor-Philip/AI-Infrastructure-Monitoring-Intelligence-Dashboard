"""
Role-Based Access Control (RBAC) enforced at the router/dependency layer.

Three roles with increasing privilege:
  * viewer       — read-only access to data
  * admin        — viewer + manage servers and view reports
  * super_admin  — full access: audit logs, user management, emergency actions

``get_current_user`` validates the JWT access token (and the session inactivity
window), loads the user, and rejects locked/inactive accounts. The
``require_roles`` factory returns a dependency that responds 403 when the caller
lacks the required role. These are applied to routers directly — never relying
on the UI for enforcement.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.enums import UserRole
from models.user import User
from utils.security import TokenError, decode_access_token

_bearer = HTTPBearer(auto_error=True)

# Privilege ordering for hierarchical checks.
_ROLE_RANK: dict[UserRole, int] = {
    UserRole.viewer: 1,
    UserRole.admin: 2,
    UserRole.super_admin: 3,
}


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve and validate the authenticated user from the bearer access token."""
    token = credentials.credentials
    try:
        claims = decode_access_token(token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Session inactivity timeout: reject tokens idle beyond the configured window.
    issued_at = claims.get("iat")
    if issued_at is not None:
        idle_seconds = datetime.now(timezone.utc).timestamp() - float(issued_at)
        if idle_seconds > settings.SESSION_INACTIVITY_TIMEOUT_MINUTES * 60:
            # Record the expiry event durably (explicit commit: the 401 we raise
            # below would otherwise roll back the get_db transaction).
            from services.audit_service import record_event

            ip = request.client.host if request.client else None
            await record_event(
                db, event_type="session_expired", success=False,
                user_id=claims.get("sub"), ip_address=ip,
                description="Session expired due to inactivity timeout.",
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to inactivity",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user = (
        await db.execute(select(User).where(User.id == claims.get("sub")))
    ).scalar_one_or_none()

    if user is None or not user.is_active or user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive, locked, or does not exist",
        )

    # Expose the caller's role/id for downstream auditing.
    request.state.user_id = str(user.id)
    request.state.user_role = user.role.value
    return user


def require_roles(*allowed: UserRole):
    """Dependency factory: allow only the listed roles, else 403."""

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _checker


def require_min_role(minimum: UserRole):
    """Dependency factory: allow the given role or anything more privileged."""

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if _ROLE_RANK[current_user.role] < _ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _checker


# Convenience dependencies for common privilege levels.
require_viewer = require_min_role(UserRole.viewer)          # any authenticated user
require_admin = require_min_role(UserRole.admin)            # admin or super_admin
require_super_admin = require_roles(UserRole.super_admin)   # super_admin only

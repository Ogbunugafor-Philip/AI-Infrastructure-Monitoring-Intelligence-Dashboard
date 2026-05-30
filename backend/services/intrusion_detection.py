"""
Intrusion detection: monitors failed login attempts per source IP.

When the number of failed logins from one IP within
``INTRUSION_ALERT_WINDOW_MINUTES`` reaches ``INTRUSION_FAILED_LOGIN_THRESHOLD``
(both from .env), an email alert is sent immediately via aiosmtplib and the
trigger is recorded in ``audit_logs``. Callers can also use
:func:`is_ip_temporarily_blocked` to enforce a temporary lockout.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.audit_log import AuditLog
from services.email_service import send_email

FAILED_LOGIN_EVENT = "login_failed"
INTRUSION_EVENT = "intrusion_detected"


async def count_recent_failed_logins(db: AsyncSession, ip_address: str) -> int:
    """Count failed-login audit entries for an IP within the alert window."""
    window_start = datetime.now(timezone.utc) - timedelta(
        minutes=settings.INTRUSION_ALERT_WINDOW_MINUTES
    )
    stmt = (
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.event_type == FAILED_LOGIN_EVENT,
            AuditLog.ip_address == ip_address,
            AuditLog.success.is_(False),
            AuditLog.created_at >= window_start,
        )
    )
    return int((await db.execute(stmt)).scalar_one())


async def is_ip_temporarily_blocked(db: AsyncSession, ip_address: str) -> bool:
    """True if the IP has met/exceeded the failure threshold within the window."""
    recent = await count_recent_failed_logins(db, ip_address)
    return recent >= settings.INTRUSION_FAILED_LOGIN_THRESHOLD


async def evaluate_failed_login(
    db: AsyncSession, ip_address: str, *, email_attempted: str | None = None
) -> bool:
    """
    Evaluate whether the latest failed login from ``ip_address`` crosses the
    intrusion threshold. If so, send an alert email and record an audit entry.

    Returns True if an intrusion alert was triggered.
    """
    recent = await count_recent_failed_logins(db, ip_address)
    if recent < settings.INTRUSION_FAILED_LOGIN_THRESHOLD:
        return False

    subject = "[AI Infra Monitoring] Intrusion alert: repeated failed logins"
    body = (
        "Security alert from the AI Infrastructure Monitoring Dashboard.\n\n"
        f"Source IP: {ip_address}\n"
        f"Failed login attempts in the last "
        f"{settings.INTRUSION_ALERT_WINDOW_MINUTES} minute(s): {recent}\n"
        f"Threshold: {settings.INTRUSION_FAILED_LOGIN_THRESHOLD}\n"
        f"Account targeted: {email_attempted or 'unknown'}\n"
        f"Detected at: {datetime.now(timezone.utc).isoformat()}\n\n"
        "Further attempts from this IP are being temporarily blocked."
    )
    await send_email(subject, body)

    db.add(
        AuditLog(
            user_id=None,
            event_type=INTRUSION_EVENT,
            event_description=(
                f"Intrusion threshold reached: {recent} failed logins from {ip_address} "
                f"within {settings.INTRUSION_ALERT_WINDOW_MINUTES} min."
            ),
            ip_address=ip_address,
            success=False,
        )
    )
    await db.flush()
    return True

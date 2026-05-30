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
from services import email_templates as T
from services.email_service import send_html_email


def build_intrusion_alert_html(ip: str, attempts: int, window_minutes: int, username) -> str:
    """Professional HTML for the intrusion-detection alert email (Type 2)."""
    audit_url = (settings.APP_URL or "").rstrip("/") + "/audit-logs"
    details = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;">'
        f'<tr><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;width:45%;">IP Address</td>'
        f'<td style="padding:10px 12px;border:1px solid #e2e8f0;">'
        f'<span style="background:{T.RED};color:#fff;font-weight:bold;padding:3px 10px;border-radius:6px;'
        f'font-family:{T.MONO};">{T.esc(ip)}</span></td></tr>'
        f'<tr style="background:#f8fafc;"><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Failed attempts</td>'
        f'<td style="padding:10px 12px;color:{T.RED};font-size:20px;font-weight:bold;border:1px solid #e2e8f0;">{attempts}</td></tr>'
        f'<tr><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Time window</td>'
        f'<td style="padding:10px 12px;color:{T.NAVY};font-size:14px;font-weight:600;border:1px solid #e2e8f0;">Last {window_minutes} minute(s)</td></tr>'
        f'<tr style="background:#f8fafc;"><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Targeted username</td>'
        f'<td style="padding:10px 12px;color:{T.NAVY};font-size:14px;font-weight:600;border:1px solid #e2e8f0;">{T.esc(username or "unknown")}</td></tr>'
        '</table>'
    )
    meaning = (
        f'<div style="background:{T.CARD};color:{T.TEXT};font-size:15px;line-height:1.7;padding:16px;border-radius:8px;">'
        f"Someone at IP address {T.esc(ip)} has attempted to log into your dashboard {attempts} times in the "
        f"last {window_minutes} minutes. This may indicate a brute-force attack. Further attempts from this IP "
        f"are being temporarily blocked.</div>"
    )
    actions = T.numbered_cards([
        "Check if this is you or someone you authorized.",
        "If unknown, consider blocking this IP at the firewall.",
        "Check your audit logs for more details.",
        "If suspicious, change your password immediately.",
    ], badge_color=T.RED)

    content = (
        T.header_bar("AI Infrastructure Monitor", T.now_iso())
        + T.banner("⚠️ SECURITY ALERT", T.RED)
        + f'<tr><td style="background:#7f1d1d;padding:8px 24px;text-align:center;color:#fecaca;font-size:13px;">Suspicious Login Activity Detected</td></tr>'
        + f'<tr><td style="padding:20px 24px;text-align:center;"><div style="font-size:40px;">🚨</div>'
          f'<div style="font-size:18px;font-weight:bold;color:{T.NAVY};margin-top:6px;">Multiple Failed Login Attempts</div></td></tr>'
        + T.section("Alert Details", details, accent=T.RED)
        + T.section("What This Means", meaning, accent=T.YELLOW)
        + T.section("Recommended Actions", actions, accent=T.RED)
        + T.section("Quick Link", T.button("View Audit Logs", audit_url, T.BLUE))
        + T.footer(["This alert was generated automatically by AI Infrastructure Monitor.",
                    "You are receiving this because you are the Super Admin."])
    )
    return T.shell(content, preheader=f"{attempts} failed logins from {ip}")

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

    html = build_intrusion_alert_html(
        ip_address, recent, settings.INTRUSION_ALERT_WINDOW_MINUTES, email_attempted
    )
    await send_html_email(
        subject="🚨 [AI Infra] Security Alert: repeated failed logins",
        html_body=html,
        text_body=(
            f"Security alert: {recent} failed login attempts from {ip_address} in the last "
            f"{settings.INTRUSION_ALERT_WINDOW_MINUTES} minutes."
        ),
    )

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

"""
Daily AI report email.

``send_daily_report_email`` renders a colour-coded HTML summary of an AI report
and sends it to SMTP_TO_EMAIL via aiosmtplib. Every attempt is recorded in
audit_logs. SMTP credentials are never logged.
"""
from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from services.audit_service import record_event

logger = logging.getLogger("ai_infra.report_email")

EMAIL_EVENT = "report_email_sent"


def _risk_color(score: int) -> str:
    if score >= 7:
        return "#ef4444"  # red
    if score >= 4:
        return "#f59e0b"  # yellow
    return "#10b981"      # green


def _list_html(items) -> str:
    if not items:
        return "<li style='color:#94a3b8'>None</li>"
    return "".join(f"<li>{str(i)}</li>" for i in items)


def _build_html(server_name: str, server_ip: str, report: dict) -> str:
    score = int(report.get("risk_score") or 5)
    color = _risk_color(score)
    level = report.get("risk_level") or "—"
    summary = report.get("summary") or "No summary available."
    return f"""\
<html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px">
  <div style="max-width:640px;margin:auto;background:#1e293b;border-radius:12px;padding:24px">
    <h2 style="margin:0 0 4px">AI Infrastructure Health Report</h2>
    <p style="color:#94a3b8;margin:0 0 16px">{server_name} &middot; {server_ip}</p>
    <div style="display:inline-block;background:{color};color:#0b1220;font-weight:bold;
                padding:8px 16px;border-radius:8px;font-size:18px">
      Risk Score: {score}/10 ({level})
    </div>
    <h3 style="margin-top:24px">Summary</h3>
    <p style="line-height:1.5">{summary}</p>
    <h3>Key Findings</h3>
    <ul>{_list_html(report.get("key_findings"))}</ul>
    <h3>Recommended Actions</h3>
    <ul>{_list_html(report.get("recommended_actions"))}</ul>
    <p style="color:#64748b;font-size:12px;margin-top:24px">
      AI Infrastructure Monitoring &amp; Intelligence Dashboard
    </p>
  </div>
</body></html>"""


async def send_daily_report_email(
    db: AsyncSession | None,
    server,
    report: dict,
) -> bool:
    """Send the HTML AI report email. Returns True on success."""
    recipient = settings.SMTP_TO_EMAIL
    if not (settings.SMTP_HOST and settings.SMTP_USERNAME and recipient):
        logger.warning("SMTP not configured; skipping report email")
        return False

    score = int(report.get("risk_score") or 5)
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    message["To"] = recipient
    message["Subject"] = f"[AI Infra] Health report for {server.name} — risk {score}/10"
    message.set_content(report.get("summary") or "AI report attached.")  # plaintext fallback
    message.add_alternative(
        _build_html(server.name, server.ip_address, report), subtype="html"
    )

    success = False
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_USE_TLS,
            timeout=20,
        )
        success = True
    except Exception as exc:  # noqa: BLE001 - emailing must not crash the pipeline
        logger.error("Report email failed: %s", type(exc).__name__)

    if db is not None:
        await record_event(
            db,
            event_type=EMAIL_EVENT,
            success=success,
            target_server_id=server.id,
            description=(
                f"Daily AI report email {'sent' if success else 'failed'} for "
                f"{server.name} (risk {score}/10)."
            ),
        )
        await db.commit()
    return success

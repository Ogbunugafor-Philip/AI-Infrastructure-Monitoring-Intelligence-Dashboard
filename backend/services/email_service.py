"""
Async email delivery via aiosmtplib using SMTP settings from .env.

Used for security alerts (e.g. intrusion detection). Failures are swallowed and
returned as ``False`` so that alerting never breaks the auth request path; the
SMTP password is never logged.
"""
from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from config import settings

logger = logging.getLogger("ai_infra.email")


async def send_email(subject: str, body: str, *, to_email: str | None = None) -> bool:
    """Send a plaintext email. Returns True on success, False on any failure."""
    recipient = to_email or settings.SMTP_TO_EMAIL
    if not (settings.SMTP_HOST and settings.SMTP_USERNAME and recipient):
        logger.warning("SMTP not fully configured; skipping email send")
        return False

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_USE_TLS,
            timeout=15,
        )
        logger.info("Security email sent to recipient")  # no address/secret logged
        return True
    except Exception as exc:  # noqa: BLE001 - alerting must never raise
        # Log only the exception type, never message content or credentials.
        logger.error("Failed to send security email: %s", type(exc).__name__)
        return False


async def send_html_email(
    subject: str,
    html_body: str,
    *,
    text_body: str | None = None,
    to_email: str | None = None,
) -> bool:
    """Send a multipart (plaintext + HTML) email. Returns True on success."""
    recipient = to_email or settings.SMTP_TO_EMAIL
    if not (settings.SMTP_HOST and settings.SMTP_USERNAME and recipient):
        logger.warning("SMTP not fully configured; skipping email send")
        return False

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    message["To"] = recipient
    message["Subject"] = subject
    # Plaintext fallback first, then the HTML alternative.
    message.set_content(text_body or "This email is best viewed in an HTML-capable client.")
    message.add_alternative(html_body, subtype="html")

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
        logger.info("HTML email sent to recipient")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send HTML email: %s", type(exc).__name__)
        return False

"""
Email alerts for privileged actions (approval, cancellation, execution, and the
emergency kill switch). All go to SMTP_TO_EMAIL via the shared email service.
Output is truncated; no credentials are ever included.
"""
from __future__ import annotations

from datetime import datetime, timezone

from services.email_service import send_email

_OUTPUT_LIMIT = 4000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def notify_high_risk_approved(*, requester: str, confirmer: str, server, command_string: str) -> bool:
    body = (
        "A HIGH RISK action has been approved via dual confirmation.\n\n"
        f"Requested by: {requester}\n"
        f"Confirmed by: {confirmer}\n"
        f"Server: {server.name} ({server.ip_address})\n"
        f"Command: {command_string}\n"
        f"Time: {_now()}\n"
    )
    return await send_email("[AI Infra] High-risk action approved", body)


async def notify_action_cancelled(*, cancelled_by: str, server, command_string: str) -> bool:
    body = (
        "A pending action was cancelled.\n\n"
        f"Cancelled by: {cancelled_by}\n"
        f"Server: {server.name} ({server.ip_address})\n"
        f"Command: {command_string}\n"
        f"Time: {_now()}\n"
    )
    return await send_email("[AI Infra] Action cancelled", body)


async def notify_action_executed(
    *, triggered_by: str, confirmed_by: str | None, server, command_string: str,
    risk_level: str, output: str,
) -> bool:
    body = (
        "An action was executed on a monitored server.\n\n"
        f"Triggered by: {triggered_by}\n"
        f"Confirmed by: {confirmed_by or 'n/a'}\n"
        f"Server: {server.name} ({server.ip_address})\n"
        f"Risk level: {risk_level}\n"
        f"Command: {command_string}\n"
        f"Time: {_now()}\n\n"
        f"Output:\n{(output or '')[:_OUTPUT_LIMIT]}\n"
    )
    return await send_email(
        f"[AI Infra] Action executed ({risk_level}) on {server.name}", body
    )


async def notify_emergency_kill(*, triggered_by: str, server, cancelled_actions: int) -> bool:
    body = (
        "EMERGENCY KILL SWITCH ACTIVATED.\n\n"
        f"Triggered by (Super Admin): {triggered_by}\n"
        f"Server: {server.name} ({server.ip_address})\n"
        f"SSH credentials revoked: yes\n"
        f"Pending/approved actions cancelled: {cancelled_actions}\n"
        f"Server status set to: offline\n"
        f"Time: {_now()}\n"
    )
    return await send_email(
        f"[AI Infra] EMERGENCY KILL on {server.name}", body
    )

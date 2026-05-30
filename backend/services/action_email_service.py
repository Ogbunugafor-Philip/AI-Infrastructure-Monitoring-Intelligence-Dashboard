"""
HTML email alerts for privileged actions and server registration.
All go to SMTP_TO_EMAIL via the shared HTML email sender. No credentials are
ever included; command output is truncated.
"""
from __future__ import annotations

from services import email_templates as T
from services.email_service import send_html_email

_OUTPUT_LIMIT = 6000

_RISK_BG = {"low": T.BLUE, "medium": T.YELLOW, "high": T.RED}


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="display:inline-block;background:{color};color:#fff;font-weight:bold;'
        f'padding:2px 10px;border-radius:6px;font-size:12px;">{T.esc(text)}</span>'
    )


# --------------------------------------------------------------------------- #
# Type 3 — New server registered                                              #
# --------------------------------------------------------------------------- #
async def notify_server_registered(*, server, registered_by: str, auth_method: str) -> bool:
    details = T.info_table([
        ("Server IP", T.esc(server.ip_address)),
        ("SSH Port", T.esc(server.ssh_port)),
        ("Authentication Method", T.esc(auth_method)),
        ("Registered By", T.esc(registered_by)),
        ("Registration Time", T.now_iso()),
    ])
    content = (
        T.header_bar("AI Infrastructure Monitor", T.now_iso())
        + T.banner("✅ New Server Registered", T.BLUE)
        + f'<tr><td style="padding:22px 24px 6px;text-align:center;">'
          f'<div style="font-size:24px;font-weight:bold;color:{T.NAVY};">{T.esc(server.name)}</div>'
          f'<div style="margin-top:8px;">{_badge("Connection Verified", T.GREEN)}</div></td></tr>'
        + T.section("Server Details", details)
        + T.footer(T.STANDARD_FOOTER)
    )
    html = T.shell(content, preheader=f"New server registered: {server.name}")
    return await send_html_email(
        subject=f"[AI Infra] New server registered: {server.name}",
        html_body=html,
        text_body=f"New server registered: {server.name} ({server.ip_address}) by {registered_by}.",
    )


# --------------------------------------------------------------------------- #
# Type 4 — Action executed                                                    #
# --------------------------------------------------------------------------- #
async def notify_action_executed(
    *, triggered_by: str, confirmed_by: str | None, server, command_string: str,
    risk_level: str, output: str,
) -> bool:
    bg = _RISK_BG.get(risk_level, T.BLUE)
    details = T.info_table([
        ("Server", f"{T.esc(server.name)} ({T.esc(server.ip_address)})"),
        ("Action", '<span style="font-family:%s;">executed</span>' % T.MONO),
        ("Risk Level", _badge(risk_level.upper(), bg)),
        ("Executed By", T.esc(triggered_by)),
        ("Execution Time", T.now_iso()),
    ])
    confirmed = ""
    if confirmed_by:
        confirmed = T.section(
            "Confirmed By",
            f'<div style="font-size:14px;color:{T.NAVY};">Dual confirmation provided by '
            f'<strong>{T.esc(confirmed_by)}</strong>.</div>',
            accent=T.GREEN,
        )
    content = (
        T.header_bar("AI Infrastructure Monitor", T.now_iso())
        + T.banner("⚡ Server Action Executed", bg)
        + T.section(
            "Action Details",
            details + '<div style="height:10px;"></div>'
            + f'<div style="color:{T.MUTED};font-size:12px;margin-bottom:4px;">Command executed</div>'
            + T.code_block(command_string),
            accent=bg,
        )
        + T.section("Command Output", T.code_block(output[:_OUTPUT_LIMIT] or "(no output)", max_height=320))
        + confirmed
        + T.footer(T.STANDARD_FOOTER)
    )
    html = T.shell(content, preheader=f"Action executed on {server.name} ({risk_level})")
    return await send_html_email(
        subject=f"[AI Infra] Action executed ({risk_level}) on {server.name}",
        html_body=html,
        text_body=f"Action executed on {server.name} ({server.ip_address}) by {triggered_by}.",
    )


# --------------------------------------------------------------------------- #
# High-risk approved / cancelled                                              #
# --------------------------------------------------------------------------- #
async def notify_high_risk_approved(*, requester: str, confirmer: str, server, command_string: str) -> bool:
    details = T.info_table([
        ("Server", f"{T.esc(server.name)} ({T.esc(server.ip_address)})"),
        ("Requested By", T.esc(requester)),
        ("Confirmed By", T.esc(confirmer)),
        ("Approved At", T.now_iso()),
    ])
    content = (
        T.header_bar("AI Infrastructure Monitor", T.now_iso())
        + T.banner("✅ High-Risk Action Approved", T.GREEN)
        + T.section("Approval Details", details + '<div style="height:10px;"></div>' + T.code_block(command_string), accent=T.GREEN)
        + T.footer(T.STANDARD_FOOTER)
    )
    return await send_html_email(
        subject=f"[AI Infra] High-risk action approved on {server.name}",
        html_body=T.shell(content), text_body=f"High-risk action approved on {server.name}.",
    )


async def notify_action_cancelled(*, cancelled_by: str, server, command_string: str) -> bool:
    details = T.info_table([
        ("Server", f"{T.esc(server.name)} ({T.esc(server.ip_address)})"),
        ("Cancelled By", T.esc(cancelled_by)),
        ("Cancelled At", T.now_iso()),
    ])
    content = (
        T.header_bar("AI Infrastructure Monitor", T.now_iso())
        + T.banner("🚫 Action Cancelled", T.MUTED)
        + T.section("Cancellation Details", details + '<div style="height:10px;"></div>' + T.code_block(command_string), accent=T.MUTED)
        + T.footer(T.STANDARD_FOOTER)
    )
    return await send_html_email(
        subject=f"[AI Infra] Action cancelled on {server.name}",
        html_body=T.shell(content), text_body=f"Action cancelled on {server.name}.",
    )

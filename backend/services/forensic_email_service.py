"""
Emergency kill-switch forensic incident report email (Type 5).

Renders a comprehensive HTML security-incident report when the emergency kill
switch is activated. Accepts an optional ``forensic_data`` dict; any section
without data degrades gracefully (e.g. "No persistence mechanisms detected").
"""
from __future__ import annotations

from services import email_templates as T
from services.email_service import send_html_email

_THREAT_BG = {"critical": "#7f1d1d", "high": "#9a3412", "medium": "#854d0e"}


def _green_box(html_inner: str) -> str:
    return (
        f'<div style="background:#052e16;border:1px solid {T.GREEN};border-left:4px solid {T.GREEN};'
        f'border-radius:8px;padding:14px;color:#bbf7d0;font-size:14px;line-height:1.7;">{html_inner}</div>'
    )


def _red_box(text: str) -> str:
    return (
        f'<div style="background:#2d1515;border-left:4px solid {T.RED};border-radius:8px;'
        f'padding:12px;color:#fecaca;font-size:14px;margin-bottom:8px;">{T.esc(text)}</div>'
    )


def build_forensic_html(*, triggered_by: str, server, cancelled_actions: int, forensic_data: dict | None) -> str:
    fd = forensic_data or {}
    threat_level = str(fd.get("threat_level", "critical")).lower()
    threat_score = fd.get("threat_score", 10)
    threat_bg = _THREAT_BG.get(threat_level, "#7f1d1d")

    # Header (full red)
    header = (
        f'<tr><td style="background:{T.RED};padding:24px;text-align:center;">'
        f'<div style="font-size:22px;font-weight:bold;color:#ffffff;">🚨 SECURITY INCIDENT REPORT</div>'
        f'<div style="font-size:14px;color:#fee2e2;margin-top:4px;">Emergency Kill Switch Activated</div>'
        f'<div style="font-size:20px;font-weight:bold;color:#ffffff;margin-top:12px;">{T.esc(server.name)}</div>'
        f'<div style="font-size:14px;color:#fecaca;font-family:{T.MONO};">{T.esc(server.ip_address)}</div>'
        f'<div style="font-size:12px;color:#fecaca;margin-top:8px;">Triggered {T.now_iso()}</div>'
        f'</td></tr>'
    )

    threat_banner = (
        f'<tr><td style="background:{threat_bg};padding:14px 24px;text-align:center;color:#ffffff;">'
        f'<span style="font-size:18px;font-weight:bold;">THREAT LEVEL: {T.esc(threat_level.upper())}</span>'
        f'<span style="font-size:14px;margin-left:10px;color:#fecaca;">Threat score: {T.esc(threat_score)} / 10</span>'
        f'</td></tr>'
    )

    # Executive summary
    summary_text = fd.get("executive_summary") or (
        f"The emergency kill switch was activated for {server.name} ({server.ip_address}) by "
        f"{triggered_by}. All stored SSH credentials for this server have been revoked and all "
        f"pending actions cancelled. The server has been disconnected from the monitoring dashboard "
        f"pending manual investigation."
    )
    exec_summary = (
        f'<div style="background:#1f2937;border-left:4px solid {T.RED};border-radius:8px;padding:16px;'
        f'color:{T.TEXT};font-size:15px;line-height:1.8;">{T.esc(summary_text)}</div>'
    )

    # Intruder details
    susp_ips = fd.get("suspicious_ips") or []
    ip_rows = "".join(
        f'<tr><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Suspicious IP</td>'
        f'<td style="padding:10px 12px;border:1px solid #e2e8f0;">'
        f'<span style="background:{T.RED};color:#fff;font-family:{T.MONO};padding:2px 8px;border-radius:5px;">{T.esc(ip)}</span></td></tr>'
        for ip in susp_ips
    ) or (
        f'<tr><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Suspicious IPs</td>'
        f'<td style="padding:10px 12px;color:{T.NAVY};font-size:14px;border:1px solid #e2e8f0;">None captured</td></tr>'
    )
    intruder = (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
        f'<tr style="background:#f8fafc;"><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;width:45%;">Active sessions at capture</td>'
        f'<td style="padding:10px 12px;color:{T.NAVY};font-size:14px;border:1px solid #e2e8f0;">{T.esc(fd.get("active_sessions", "not captured"))}</td></tr>'
        f'<tr><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Estimated entry method</td>'
        f'<td style="padding:10px 12px;color:{T.NAVY};font-size:14px;border:1px solid #e2e8f0;">{T.esc(fd.get("entry_method", "unknown"))}</td></tr>'
        f'<tr style="background:#f8fafc;"><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Estimated entry time</td>'
        f'<td style="padding:10px 12px;color:{T.NAVY};font-size:14px;border:1px solid #e2e8f0;">{T.esc(fd.get("entry_time", "unknown"))}</td></tr>'
        f'<tr><td style="padding:10px 12px;color:{T.MUTED};font-size:13px;border:1px solid #e2e8f0;">Usernames used/targeted</td>'
        f'<td style="padding:10px 12px;color:{T.NAVY};font-size:14px;border:1px solid #e2e8f0;">{T.esc(", ".join(fd.get("usernames", [])) or "not captured")}</td></tr>'
        f'{ip_rows}'
        '</table>'
    )

    # Recorded actions
    recorded = fd.get("recorded_actions") or []
    recorded_html = T.numbered_cards(recorded, badge_color=T.RED) if recorded else \
        f'<div style="color:{T.MUTED};font-size:14px;">No specific intruder actions were recorded.</div>'

    # Persistence
    persistence = fd.get("persistence") or []
    persistence_html = "".join(_red_box(p) for p in persistence) if persistence else \
        _green_box("✅ No persistence mechanisms detected.")

    # IOCs
    iocs = fd.get("iocs") or []
    iocs_html = "".join(T.code_block(i) + '<div style="height:6px;"></div>' for i in iocs) if iocs else \
        f'<div style="color:{T.MUTED};font-size:14px;">None identified.</div>'

    # Immediate actions
    immediate = T.numbered_cards([
        "Rotate any credentials that may have been exposed on this server.",
        "Review audit logs and authentication history for the affected window.",
        "Isolate the server from the network until confirmed clean.",
        "Rebuild or restore the server from a known-good snapshot if compromise is confirmed.",
    ], badge_color=T.RED)

    # What was wiped
    wiped = _green_box(
        "The following credentials have been revoked from the dashboard:"
        '<ul style="margin:10px 0 0 18px;padding:0;">'
        "<li><strong>SSH Password</strong> — WIPED</li>"
        "<li><strong>SSH Private Key</strong> — WIPED</li>"
        f"<li><strong>All pending actions</strong> — CANCELLED ({cancelled_actions})</li>"
        "</ul>"
        f'<div style="margin-top:10px;color:#86efac;font-size:12px;">Wiped at {T.now_iso()}</div>'
    )

    # Raw forensic evidence
    raw = fd.get("raw_evidence") or []
    if raw:
        raw_html = ""
        for item in raw:
            cmd = item.get("command", "command")
            out = item.get("output", "")
            raw_html += (
                f'<div style="color:{T.MUTED};font-size:13px;font-weight:bold;margin:12px 0 6px;">{T.esc(cmd)}</div>'
                + T.code_block(out, max_height=240)
            )
    else:
        raw_html = f'<div style="color:{T.MUTED};font-size:14px;">No raw forensic data was captured during the kill.</div>'

    footer = (
        f'<tr><td style="background:{T.RED};padding:20px 24px;text-align:center;">'
        f'<div style="color:#fff;font-size:13px;line-height:1.7;">This server has been disconnected from the monitoring dashboard.</div>'
        f'<div style="color:#fecaca;font-size:13px;line-height:1.7;">Re-register only after confirming the server is clean and secure.</div>'
        f'<div style="color:#fecaca;font-size:12px;line-height:1.7;margin-top:6px;">Generated by AI Infrastructure Monitor Emergency Response System</div>'
        f'<div style="color:#fca5a5;font-size:11px;margin-top:6px;">{T.now_iso()}</div>'
        f'</td></tr>'
    )

    content = (
        header
        + threat_banner
        + T.section("What Happened", exec_summary, accent=T.RED)
        + T.section("🕵️ Intruder Details", intruder, accent=T.RED)
        + T.section("Recorded Actions", recorded_html, accent=T.RED)
        + T.section("⚠️ Backdoors or Persistent Access Found", persistence_html, accent=T.YELLOW)
        + T.section("Indicators of Compromise", iocs_html, accent=T.YELLOW)
        + T.section("🔴 Immediate Actions Required", immediate, accent=T.RED)
        + T.section("What Was Wiped", wiped, accent=T.GREEN)
        + T.section("Raw Forensic Evidence", raw_html, accent=T.MUTED)
        + footer
    )
    return T.shell(content, preheader=f"EMERGENCY KILL: {server.name} disconnected")


async def send_emergency_kill_forensic(
    *, triggered_by: str, server, cancelled_actions: int, forensic_data: dict | None = None
) -> bool:
    html = build_forensic_html(
        triggered_by=triggered_by, server=server,
        cancelled_actions=cancelled_actions, forensic_data=forensic_data,
    )
    return await send_html_email(
        subject=f"🚨 [AI Infra] EMERGENCY KILL — security incident on {server.name}",
        html_body=html,
        text_body=f"Emergency kill switch activated on {server.name} ({server.ip_address}). Credentials revoked.",
    )

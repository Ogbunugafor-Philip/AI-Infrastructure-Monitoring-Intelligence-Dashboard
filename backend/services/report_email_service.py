"""
Daily AI report email (HTML).

Renders a professional, Gmail-friendly HTML report from an AI report dict and
the server's latest metrics, and sends it to SMTP_TO_EMAIL. Every attempt is
recorded in audit_logs. SMTP credentials are never logged.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.metric import Metric
from services import email_templates as T
from services.audit_service import record_event
from services.email_service import send_html_email

logger = logging.getLogger("ai_infra.report_email")

EMAIL_EVENT = "report_email_sent"


def _finding_dot(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ("error", "critical", "high", "failed", "unauthorized")):
        return T.RED
    if any(w in t for w in ("warning", "elevated", "unusual")):
        return T.YELLOW
    return T.GREEN


def _security_dot(text: str) -> str:
    c = _finding_dot(text)
    return c if c != T.GREEN else T.YELLOW


def build_daily_report_html(server_name: str, server_ip: str, report: dict, metric) -> str:
    score = int(report.get("risk_score") or 5)
    color = T.risk_color(score)
    word = (report.get("risk_level") or T.risk_word(score)).upper()
    health = {"CRITICAL": "Server Health: CRITICAL", "WARNING": "Server Health: WARNING"}.get(
        word, "Server Health: GOOD"
    )

    hero = (
        f'<tr><td style="background:{T.NAVY};padding:28px 24px;text-align:center;">'
        f'<div style="font-size:28px;font-weight:bold;color:#ffffff;">{T.esc(server_name)}</div>'
        f'<div style="font-size:14px;color:{T.MUTED};margin-bottom:18px;">{T.esc(server_ip)}</div>'
        f'{T.risk_circle(score, color)}'
        f'<div style="margin-top:12px;font-size:16px;font-weight:bold;color:{color};">{T.esc(word)}</div>'
        f'<div style="font-size:12px;color:{T.MUTED};margin-top:4px;">Report generated {T.now_iso()}</div>'
        f'</td></tr>'
    )

    summary = T.section("Summary", T.paragraph_box(report.get("summary") or "No summary available."))

    findings = T.section(
        "Key Findings",
        T.bullet_list(report.get("key_findings") or [], dot_color_fn=_finding_dot),
    )
    actions = T.section(
        "Recommended Actions",
        T.numbered_cards(report.get("recommended_actions") or []),
    )
    security = T.section(
        "🛡️ Security Observations",
        T.bullet_list(report.get("security_observations") or [], dot_color_fn=_security_dot),
        accent=T.RED,
    )
    performance = T.section(
        "📊 Performance",
        T.bullet_list(report.get("performance_observations") or [], default_color=T.BLUE),
        accent=T.BLUE,
    )

    cpu = metric.cpu_usage if metric else None
    ram = metric.ram_usage if metric else None
    disk = metric.disk_usage if metric else None
    metrics_snapshot = T.section(
        "Server Metrics Snapshot",
        T.metric_boxes([
            ("CPU Usage", f"{cpu:.0f}%" if cpu is not None else "—", T.usage_color(cpu)),
            ("RAM Usage", f"{ram:.0f}%" if ram is not None else "—", T.usage_color(ram)),
            ("Disk Usage", f"{disk:.0f}%" if disk is not None else "—", T.usage_color(disk)),
        ]),
    )

    content = (
        T.header_bar("AI Infrastructure Monitor", T.now_iso())
        + T.banner(health, color)
        + hero
        + summary
        + findings
        + actions
        + security
        + performance
        + metrics_snapshot
        + T.footer([
            "This report was generated automatically by AI Infrastructure Monitor.",
            "Next scheduled report in 24 hours.",
            "You are receiving this because you are the Super Admin.",
        ])
    )
    return T.shell(content, preheader=f"{health} — risk {score}/10 for {server_name}")


async def send_daily_report_email(db: AsyncSession | None, server, report: dict) -> bool:
    """Send the HTML AI report email. Returns True on success."""
    metric = None
    if db is not None:
        metric = (
            await db.execute(
                select(Metric).where(Metric.server_id == server.id)
                .order_by(Metric.collected_at.desc()).limit(1)
            )
        ).scalar_one_or_none()

    score = int(report.get("risk_score") or 5)
    html = build_daily_report_html(server.name, server.ip_address, report, metric)
    text = f"AI health report for {server.name} ({server.ip_address}) — risk {score}/10. View in an HTML client."

    success = await send_html_email(
        subject=f"[AI Infra] Health report for {server.name} — risk {score}/10",
        html_body=html,
        text_body=text,
    )

    if db is not None:
        await record_event(
            db, event_type=EMAIL_EVENT, success=success, target_server_id=server.id,
            description=f"Daily AI report email {'sent' if success else 'failed'} for {server.name} (risk {score}/10).",
        )
        await db.commit()
    return success

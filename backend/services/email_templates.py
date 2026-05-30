"""
Reusable HTML email components (inline CSS only, Gmail-friendly).

All emails are built from these helpers so styling stays consistent:
  * 600px centered container on a #f1f5f9 body
  * system font stack, body text >= 14px / line-height 1.6
  * section headings with a 3px left accent border
  * dark code blocks (Courier New)
  * standardized footer

Every helper returns an HTML string. User-supplied text is HTML-escaped.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif"
MONO = "'Courier New', Courier, monospace"

# Palette
NAVY = "#0f1117"
CARD = "#1a1d2e"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
BODY_BG = "#f1f5f9"
BLUE = "#3b82f6"
GREEN = "#22c55e"
YELLOW = "#f59e0b"
RED = "#ef4444"


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def risk_color(score) -> str:
    try:
        s = int(score)
    except (TypeError, ValueError):
        return YELLOW
    if s >= 7:
        return RED
    if s >= 4:
        return YELLOW
    return GREEN


def risk_word(score) -> str:
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "WARNING"
    if s >= 7:
        return "CRITICAL"
    if s >= 4:
        return "WARNING"
    return "HEALTHY"


def usage_color(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return MUTED
    if v > 80:
        return RED
    if v >= 60:
        return YELLOW
    return GREEN


# --------------------------------------------------------------------------- #
# Layout primitives                                                           #
# --------------------------------------------------------------------------- #
def shell(content: str, *, preheader: str = "") -> str:
    """Wrap content in the full email document (600px centered)."""
    pre = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{esc(preheader)}</div>'
        if preheader else ""
    )
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{BODY_BG};font-family:{FONT};">
{pre}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BODY_BG};padding:24px 0;">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0"
           style="width:600px;max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;
                  box-shadow:0 1px 3px rgba(0,0,0,0.12);">
      {content}
    </table>
  </td></tr>
</table>
</body></html>"""


def header_bar(left: str, right: str = "") -> str:
    """Dark navy header with left logo text and right meta text."""
    right_html = f'<td align="right" style="color:{MUTED};font-size:13px;">{esc(right)}</td>' if right else ""
    return f"""\
<tr><td style="background:{NAVY};padding:18px 24px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="color:#ffffff;font-size:18px;font-weight:bold;">🛡️ {esc(left)}</td>
    {right_html}
  </tr></table>
</td></tr>"""


def banner(text: str, bg: str, color: str = "#ffffff") -> str:
    return f"""\
<tr><td style="background:{bg};padding:14px 24px;text-align:center;
       color:{color};font-size:18px;font-weight:bold;letter-spacing:.5px;">{esc(text)}</td></tr>"""


def _td(content: str) -> str:
    return f'<tr><td style="padding:20px 24px;">{content}</td></tr>'


def section_heading(text: str, accent: str = BLUE, on_dark: bool = False) -> str:
    color = "#ffffff" if on_dark else NAVY
    return (
        f'<div style="border-left:3px solid {accent};padding-left:12px;margin:0 0 12px 0;'
        f'font-size:16px;font-weight:bold;color:{color};">{esc(text)}</div>'
    )


def section(heading: str, body_html: str, accent: str = BLUE) -> str:
    return _td(section_heading(heading, accent) + body_html)


def paragraph_box(text: str) -> str:
    return (
        f'<div style="background:{CARD};color:{TEXT};font-size:15px;line-height:1.7;'
        f'padding:16px;border-radius:8px;">{esc(text)}</div>'
    )


def code_block(text: str, max_height: int | None = None) -> str:
    style = (
        f"font-family:{MONO};background:{CARD};color:{TEXT};padding:12px;border-radius:6px;"
        f"font-size:13px;line-height:1.5;white-space:pre-wrap;word-break:break-word;overflow-x:auto;"
    )
    if max_height:
        style += f"max-height:{max_height}px;overflow-y:auto;"
    return f'<div style="{style}">{esc(text)}</div>'


def button(label: str, href: str, bg: str = BLUE) -> str:
    return (
        f'<a href="{esc(href)}" style="display:inline-block;background:{bg};color:#ffffff;'
        f'text-decoration:none;font-weight:bold;padding:12px 24px;border-radius:6px;font-size:14px;">'
        f'{esc(label)}</a>'
    )


def info_table(rows: list[tuple[str, str]]) -> str:
    body = ""
    for i, (k, v) in enumerate(rows):
        bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
        body += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:10px 12px;color:{MUTED};font-size:13px;border:1px solid #e2e8f0;width:40%;">{esc(k)}</td>'
            f'<td style="padding:10px 12px;color:{NAVY};font-size:14px;border:1px solid #e2e8f0;font-weight:600;">{v}</td>'
            f'</tr>'
        )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">{body}</table>'


def bullet_list(items: list[str], dot_color_fn=None, default_color: str = GREEN) -> str:
    if not items:
        return f'<div style="color:{MUTED};font-size:14px;">None.</div>'
    rows = ""
    for i, it in enumerate(items):
        color = dot_color_fn(it) if dot_color_fn else default_color
        sep = "border-bottom:1px solid #e2e8f0;" if i < len(items) - 1 else ""
        rows += (
            f'<tr><td style="padding:10px 0;{sep}">'
            f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td valign="top" style="width:18px;padding-top:5px;">'
            f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{color};"></span></td>'
            f'<td style="color:{NAVY};font-size:14px;line-height:1.6;">{esc(it)}</td>'
            f'</tr></table></td></tr>'
        )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'


def numbered_cards(items: list[str], badge_color: str = BLUE) -> str:
    if not items:
        return f'<div style="color:{MUTED};font-size:14px;">None.</div>'
    out = ""
    for i, it in enumerate(items):
        bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
        out += (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid #e2e8f0;border-radius:8px;margin-bottom:8px;background:{bg};"><tr>'
            f'<td valign="top" style="width:44px;padding:12px;">'
            f'<span style="display:inline-block;width:26px;height:26px;line-height:26px;text-align:center;'
            f'border-radius:50%;background:{badge_color};color:#ffffff;font-weight:bold;font-size:13px;">{i + 1}</span></td>'
            f'<td style="padding:12px 12px 12px 0;color:{NAVY};font-size:14px;line-height:1.6;">{esc(it)}</td>'
            f'</tr></table>'
        )
    return out


def metric_boxes(boxes: list[tuple[str, str, str]]) -> str:
    """boxes = [(label, value_text, color)] rendered side by side."""
    cells = ""
    for label, value, color in boxes:
        cells += (
            f'<td width="33%" style="padding:6px;">'
            f'<div style="background:{color}1a;border:1px solid {color};border-radius:8px;padding:14px;text-align:center;">'
            f'<div style="font-size:22px;font-weight:bold;color:{color};">{esc(value)}</div>'
            f'<div style="font-size:12px;color:{MUTED};margin-top:4px;">{esc(label)}</div>'
            f'</div></td>'
        )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{cells}</tr></table>'


def risk_circle(score, color: str) -> str:
    return (
        f'<div style="width:96px;height:96px;border-radius:50%;background:{color};margin:0 auto;'
        f'text-align:center;line-height:96px;color:#ffffff;font-size:38px;font-weight:bold;">{esc(score)}</div>'
    )


def footer(lines: list[str], bg: str = NAVY) -> str:
    body = "".join(
        f'<div style="color:{MUTED};font-size:12px;line-height:1.7;">{esc(ln)}</div>' for ln in lines
    )
    return (
        f'<tr><td style="background:{bg};padding:20px 24px;text-align:center;">'
        f'{body}<div style="color:#475569;font-size:11px;margin-top:8px;">{now_iso()}</div>'
        f'</td></tr>'
    )


STANDARD_FOOTER = [
    "This report was generated automatically by AI Infrastructure Monitor.",
    "You are receiving this because you are the Super Admin.",
]

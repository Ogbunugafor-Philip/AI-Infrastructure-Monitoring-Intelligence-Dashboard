#!/usr/bin/env python3
"""
Send one sample of each HTML email to SMTP_TO_EMAIL using mock data.

Usage:
    cd /root/projects/AI_Infra_Monitoring/backend
    source venv/bin/activate
    python scripts/test_emails.py
"""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from services import action_email_service as A  # noqa: E402
from services import forensic_email_service as F  # noqa: E402
from services import report_email_service as R  # noqa: E402
from services.email_service import send_html_email  # noqa: E402
from services.intrusion_detection import build_intrusion_alert_html  # noqa: E402

MOCK_SERVER = types.SimpleNamespace(
    name="prod-web-01",
    ip_address="203.0.113.42",
    ssh_port=22,
    ssh_auth_method=types.SimpleNamespace(value="key"),
)
MOCK_METRIC = types.SimpleNamespace(cpu_usage=42.0, ram_usage=88.0, disk_usage=31.0)
MOCK_REPORT = {
    "summary": "The server is operating with elevated memory usage but stable CPU and disk. "
               "No critical security issues were detected, though one service is exposed publicly. "
               "Overall the host is healthy with one area to watch.",
    "risk_score": 6,
    "risk_level": "warning",
    "key_findings": [
        "RAM usage is elevated at 88%.",
        "PostgreSQL is listening on a public interface (unauthorized exposure).",
        "No failed system services detected.",
    ],
    "recommended_actions": [
        "Restart nginx to clear stale worker connections.",
        "Clear temporary files older than 7 days to free disk space.",
        "Bind PostgreSQL to 127.0.0.1 or restrict it with the firewall.",
    ],
    "security_observations": [
        "Port 5432 (PostgreSQL) is reachable from all interfaces.",
        "No unauthorized SSH keys found.",
    ],
    "performance_observations": [
        "CPU load is within normal range.",
        "Memory pressure is rising and should be monitored.",
    ],
}


async def main() -> None:
    print(f"Sending sample emails to {settings.SMTP_TO_EMAIL} ...")
    results = {}

    # Type 1 — daily report (built with a mock metric so the snapshot has values)
    html = R.build_daily_report_html(
        MOCK_SERVER.name, MOCK_SERVER.ip_address, MOCK_REPORT, MOCK_METRIC
    )
    results["1. daily_report"] = await send_html_email(
        "[AI Infra] TEST — Daily Health Report", html
    )

    # Type 2 — intrusion alert
    results["2. intrusion_alert"] = await send_html_email(
        "🚨 [AI Infra] TEST — Security Alert",
        build_intrusion_alert_html("198.51.100.23", 5, 10, "admin@example.com"),
    )

    # Type 3 — new server registered
    results["3. server_registered"] = await A.notify_server_registered(
        server=MOCK_SERVER, registered_by="admin@example.com", auth_method="key"
    )

    # Type 4 — action executed
    results["4. action_executed"] = await A.notify_action_executed(
        triggered_by="admin@example.com",
        confirmed_by="superadmin@example.com",
        server=MOCK_SERVER,
        command_string="systemctl restart nginx && echo nginx_restarted",
        risk_level="high",
        output="nginx_restarted\n● nginx.service - A high performance web server\n   Active: active (running)",
    )

    # Type 5 — emergency kill forensic report
    results["5. forensic_kill"] = await F.send_emergency_kill_forensic(
        triggered_by="superadmin@example.com",
        server=MOCK_SERVER,
        cancelled_actions=3,
        forensic_data={
            "threat_level": "critical",
            "threat_score": 9,
            "executive_summary": "Multiple unauthorized SSH sessions were detected from a foreign IP, "
                                 "followed by privilege escalation attempts. The kill switch was triggered.",
            "active_sessions": "3 active sessions at capture",
            "entry_method": "SSH brute force",
            "entry_time": "2026-05-30 02:14 UTC",
            "suspicious_ips": ["45.155.205.99", "185.220.101.7"],
            "usernames": ["root", "admin"],
            "recorded_actions": [
                "Created a new user 'svc-backup'.",
                "Added an SSH key to /root/.ssh/authorized_keys.",
                "Downloaded a script from a remote host.",
            ],
            "persistence": ["Cron job installed in /etc/cron.d/.maint"],
            "iocs": ["45.155.205.99", "/tmp/.x/run.sh", "svc-backup"],
            "raw_evidence": [
                {"command": "who", "output": "root  pts/0  45.155.205.99  02:14"},
                {"command": "last -n 5", "output": "root pts/0 45.155.205.99 ... still logged in"},
            ],
        },
    )

    print("\nResults:")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    print("\nDone. Check the inbox of", settings.SMTP_TO_EMAIL)


if __name__ == "__main__":
    asyncio.run(main())

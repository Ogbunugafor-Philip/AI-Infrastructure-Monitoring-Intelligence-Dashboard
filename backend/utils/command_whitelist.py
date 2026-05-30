"""
Hardcoded command whitelist for remote action execution.

SECURITY MODEL — this is the single source of truth for what can ever run:
  * The whitelist is defined here as immutable mappings (MappingProxyType).
    It CANNOT be modified or extended at runtime, and no user input is ever
    added to it.
  * Callers pass a ``command_key`` only. The backend looks up the exact,
    hardcoded command string for that key and executes that string verbatim.
  * Commands are NEVER constructed by concatenating user input.

The only valid execution path is:
    string = get_command(command_key)   # raises if unknown
    <run `string` exactly over SSH>
"""
from __future__ import annotations

from types import MappingProxyType

# ---- LOW RISK: no dual confirmation, no time lock ----
_LOW = {
    "check_disk_space": "df -h",
    "check_memory": "free -m",
    "check_cpu": "top -bn1 | head -20",
    "check_uptime": "uptime",
    "check_load": "cat /proc/loadavg",
    "list_running_services": "systemctl list-units --type=service --state=running",
    "check_open_ports": "ss -tlnp",
    "check_logged_in_users": "who",
    "check_last_logins": "last -n 20",
    "check_failed_logins": "lastb -n 20 2>/dev/null || echo no_data",
    "check_network_interfaces": "ip addr show",
    "check_firewall_status": "ufw status verbose 2>/dev/null || iptables -L -n 2>/dev/null",
    "check_cron_jobs": "crontab -l 2>/dev/null || echo no_crontab",
    "check_environment_variables": "env | grep -v -E 'PASSWORD|SECRET|KEY|TOKEN|PASSWD'",
    "check_nginx_status": "systemctl status nginx --no-pager",
    "check_postgresql_status": "systemctl status postgresql --no-pager",
    "check_docker_containers": "docker ps 2>/dev/null || echo docker_not_running",
    "tail_syslog": "tail -n 50 /var/log/syslog 2>/dev/null || tail -n 50 /var/log/messages 2>/dev/null",
    "tail_auth_log": "tail -n 50 /var/log/auth.log 2>/dev/null || tail -n 50 /var/log/secure 2>/dev/null",
    "tail_nginx_error": "tail -n 50 /var/log/nginx/error.log 2>/dev/null || echo log_unavailable",
}

# ---- MEDIUM RISK: single confirmation + password re-entry, no time lock ----
_MEDIUM = {
    "clear_temp_files": "find /tmp -type f -mtime +7 -delete && echo temp_files_cleared",
    "clear_old_logs": "journalctl --vacuum-time=30d && echo old_logs_cleared",
    "reload_nginx": "systemctl reload nginx && echo nginx_reloaded",
    "reload_postgresql": "systemctl reload postgresql && echo postgresql_reloaded",
    "flush_dns_cache": "systemd-resolve --flush-caches && echo dns_cache_flushed",
    "check_disk_inodes": "df -i",
    "list_large_files": "find / -type f -size +100M -not -path '/proc/*' -not -path '/sys/*' 2>/dev/null | head -20",
    "check_zombie_processes": "ps aux | awk '$8==\"Z\"' | head -20",
}

# ---- HIGH RISK: dual confirmation (2nd admin/super) + 60s time lock ----
_HIGH = {
    "restart_nginx": "systemctl restart nginx && echo nginx_restarted",
    "restart_postgresql": "systemctl restart postgresql && echo postgresql_restarted",
    "restart_docker": "systemctl restart docker && echo docker_restarted",
    "kill_zombie_processes": "kill -9 $(ps aux | awk '$8==\"Z\" {print $2}') 2>/dev/null && echo zombies_killed",
    "rotate_logs": "logrotate -f /etc/logrotate.conf && echo logs_rotated",
    "clear_failed_systemd": "systemctl reset-failed && echo failed_units_cleared",
    "reboot_server": "shutdown -r +1 'Scheduled reboot from AI Infra Dashboard' && echo reboot_scheduled",
}

# Human-readable descriptions (display only; never executed).
_DESCRIPTIONS = {
    "check_disk_space": "Show disk space usage per filesystem",
    "check_memory": "Show memory usage",
    "check_cpu": "Show top CPU consumers",
    "check_uptime": "Show system uptime",
    "check_load": "Show load average",
    "list_running_services": "List running systemd services",
    "check_open_ports": "List listening TCP ports",
    "check_logged_in_users": "Show logged-in users",
    "check_last_logins": "Show recent successful logins",
    "check_failed_logins": "Show recent failed login attempts",
    "check_network_interfaces": "Show network interfaces",
    "check_firewall_status": "Show firewall status",
    "check_cron_jobs": "Show the user's cron jobs",
    "check_environment_variables": "Show env vars (secrets filtered)",
    "check_nginx_status": "Show nginx service status",
    "check_postgresql_status": "Show PostgreSQL service status",
    "check_docker_containers": "List running Docker containers",
    "tail_syslog": "Tail the system log (50 lines)",
    "tail_auth_log": "Tail the auth log (50 lines)",
    "tail_nginx_error": "Tail the nginx error log (50 lines)",
    "clear_temp_files": "Delete /tmp files older than 7 days",
    "clear_old_logs": "Vacuum journald logs older than 30 days",
    "reload_nginx": "Reload nginx configuration",
    "reload_postgresql": "Reload PostgreSQL configuration",
    "flush_dns_cache": "Flush the systemd-resolved DNS cache",
    "check_disk_inodes": "Show inode usage per filesystem",
    "list_large_files": "List files larger than 100MB",
    "check_zombie_processes": "List zombie processes",
    "restart_nginx": "Restart the nginx service",
    "restart_postgresql": "Restart the PostgreSQL service",
    "restart_docker": "Restart the Docker service",
    "kill_zombie_processes": "Kill zombie processes",
    "rotate_logs": "Force a logrotate run",
    "clear_failed_systemd": "Reset failed systemd units",
    "reboot_server": "Schedule a server reboot in 1 minute",
}

# Immutable views — these objects reject mutation at runtime.
LOW_RISK_COMMANDS = MappingProxyType(dict(_LOW))
MEDIUM_RISK_COMMANDS = MappingProxyType(dict(_MEDIUM))
HIGH_RISK_COMMANDS = MappingProxyType(dict(_HIGH))

# command_key -> risk level
_RISK_BY_KEY = MappingProxyType({
    **{k: "low" for k in _LOW},
    **{k: "medium" for k in _MEDIUM},
    **{k: "high" for k in _HIGH},
})

# command_key -> exact command string (single flat immutable map)
_ALL_COMMANDS = MappingProxyType({**_LOW, **_MEDIUM, **_HIGH})


class CommandNotWhitelistedError(KeyError):
    """Raised when a command_key is not present in the whitelist."""


def is_whitelisted(command_key: str) -> bool:
    return command_key in _ALL_COMMANDS


def get_command(command_key: str) -> str:
    """Return the exact hardcoded command string for a key (raises if unknown)."""
    if command_key not in _ALL_COMMANDS:
        raise CommandNotWhitelistedError(f"Command key '{command_key}' is not whitelisted")
    return _ALL_COMMANDS[command_key]


def get_risk_level(command_key: str) -> str:
    if command_key not in _RISK_BY_KEY:
        raise CommandNotWhitelistedError(f"Command key '{command_key}' is not whitelisted")
    return _RISK_BY_KEY[command_key]


def get_catalog() -> dict[str, list[dict]]:
    """Return the whitelist organized by risk level for display (no secrets)."""
    def items(mapping, level):
        return [
            {
                "command_key": key,
                "description": _DESCRIPTIONS.get(key, key),
                "risk_level": level,
                "command_string": cmd,
            }
            for key, cmd in mapping.items()
        ]

    return {
        "low": items(LOW_RISK_COMMANDS, "low"),
        "medium": items(MEDIUM_RISK_COMMANDS, "medium"),
        "high": items(HIGH_RISK_COMMANDS, "high"),
    }

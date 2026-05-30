"""
Startup environment validation.

``verify_required_env`` checks that every required variable from .env is present
and non-empty, and that key invariants hold (e.g. the encryption key yields 32
bytes). On failure it raises ``EnvValidationError`` with the list of missing /
invalid variable NAMES only — values are never included, so secrets cannot leak
into logs or stack traces.
"""
from __future__ import annotations

from config import settings

# Variables that MUST be present and non-empty for the app to run safely.
REQUIRED_VARS: tuple[str, ...] = (
    "APP_NAME",
    "APP_ENV",
    "DATABASE_USER",
    "DATABASE_PASSWORD",
    "DATABASE_NAME",
    "DATABASE_HOST",
    "DATABASE_PORT",
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    "ARGON2_TIME_COST",
    "ARGON2_MEMORY_COST",
    "ARGON2_PARALLELISM",
    "SSH_ENCRYPTION_MASTER_KEY",
    "RATE_LIMIT_LOGIN_MAX_ATTEMPTS",
    "RATE_LIMIT_LOGIN_WINDOW_SECONDS",
    "RATE_LIMIT_API_MAX_REQUESTS",
    "RATE_LIMIT_API_WINDOW_SECONDS",
    "SESSION_INACTIVITY_TIMEOUT_MINUTES",
    "REDIS_HOST",
    "REDIS_PORT",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM_EMAIL",
    "SMTP_TO_EMAIL",
    "INTRUSION_FAILED_LOGIN_THRESHOLD",
    "INTRUSION_ALERT_WINDOW_MINUTES",
)


class EnvValidationError(RuntimeError):
    """Raised at startup when required configuration is missing or invalid."""


def verify_required_env() -> None:
    """Validate required configuration. Raises EnvValidationError listing only names."""
    missing: list[str] = []
    for name in REQUIRED_VARS:
        value = getattr(settings, name, None)
        # Treat empty strings as missing; 0 / False are valid configured values.
        if value is None or (isinstance(value, str) and value.strip() == ""):
            missing.append(name)

    problems: list[str] = []
    if missing:
        problems.append("Missing or empty required variables: " + ", ".join(sorted(missing)))

    # Invariant: the master encryption key must yield a usable 256-bit key.
    try:
        from utils.encryption import _KEY  # local import to avoid cycles at module load

        if len(_KEY) != 32:
            problems.append("SSH_ENCRYPTION_MASTER_KEY does not derive a 32-byte key")
    except Exception:  # pragma: no cover - defensive
        problems.append("SSH_ENCRYPTION_MASTER_KEY could not be processed")

    # Invariant: JWT secret should be reasonably long.
    if settings.JWT_SECRET_KEY and len(settings.JWT_SECRET_KEY) < 32:
        problems.append("JWT_SECRET_KEY is too short (min 32 chars recommended)")

    if problems:
        raise EnvValidationError(
            "Environment validation failed:\n  - " + "\n  - ".join(problems)
        )

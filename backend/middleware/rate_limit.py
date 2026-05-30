"""
slowapi rate limiting, backed by Redis so limits hold across worker processes.

- Auth endpoints: RATE_LIMIT_LOGIN_MAX_ATTEMPTS per RATE_LIMIT_LOGIN_WINDOW_SECONDS
- All other endpoints: RATE_LIMIT_API_MAX_REQUESTS per RATE_LIMIT_API_WINDOW_SECONDS
Exceeding a limit yields HTTP 429 with a clear JSON message.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings

# Human-readable limit strings consumed by slowapi decorators.
LOGIN_RATE_LIMIT = (
    f"{settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS}"
    f"/{settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS} seconds"
)
API_RATE_LIMIT = (
    f"{settings.RATE_LIMIT_API_MAX_REQUESTS}"
    f"/{settings.RATE_LIMIT_API_WINDOW_SECONDS} seconds"
)

# Redis storage URI from .env (falls back to in-memory if Redis is unreachable).
_redis_storage_uri = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[API_RATE_LIMIT],   # applies globally unless overridden
    storage_uri=_redis_storage_uri,
    strategy="fixed-window",
)

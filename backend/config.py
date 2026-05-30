"""
Central application configuration.

Every value is loaded from the project-root ``.env`` file via ``python-decouple``.
No secret is ever logged or printed here — only consumed.

The async database URL is constructed from the discrete ``DATABASE_*`` components
using SQLAlchemy's ``URL.create`` so that special characters in the password
(e.g. ``@``) are URL-encoded correctly. This avoids relying on a hand-written
``DATABASE_URL`` string, which is fragile and, in the current ``.env``, still
carries a placeholder password.
"""
from functools import lru_cache
from pathlib import Path

from decouple import Config, RepositoryEnv
from sqlalchemy import URL

# ---------------------------------------------------------------------------
# Resolve and load the .env file from the project root (one level above backend/)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent          # .../backend
PROJECT_ROOT = BASE_DIR.parent                       # .../AI_Infra_Monitoring
ENV_PATH = PROJECT_ROOT / ".env"

config = Config(RepositoryEnv(str(ENV_PATH)))


class Settings:
    """Typed, validated view over the .env file."""

    # ----- Application -----
    APP_NAME: str = config("APP_NAME", default="AI Infrastructure Monitoring Dashboard")
    APP_ENV: str = config("APP_ENV", default="production")
    APP_DEBUG: bool = config("APP_DEBUG", default=False, cast=bool)
    APP_URL: str = config("APP_URL", default="").strip()
    FRONTEND_URL: str = config("FRONTEND_URL", default="").strip()

    # ----- Backend server -----
    BACKEND_HOST: str = config("BACKEND_HOST", default="127.0.0.1")
    BACKEND_PORT: int = config("BACKEND_PORT", default=8002, cast=int)

    # ----- Frontend server -----
    FRONTEND_HOST: str = config("FRONTEND_HOST", default="127.0.0.1")
    FRONTEND_PORT: int = config("FRONTEND_PORT", default=3001, cast=int)

    # ----- Database -----
    DATABASE_USER: str = config("DATABASE_USER")
    DATABASE_PASSWORD: str = config("DATABASE_PASSWORD")
    DATABASE_NAME: str = config("DATABASE_NAME")
    DATABASE_HOST: str = config("DATABASE_HOST", default="localhost")
    DATABASE_PORT: int = config("DATABASE_PORT", default=5432, cast=int)
    # The raw URL is kept for reference but NOT used for connecting.
    DATABASE_URL_RAW: str = config("DATABASE_URL", default="")

    # ----- Authentication / JWT -----
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = config(
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default=15, cast=int
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = config(
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int
    )

    # ----- Argon2 password hashing -----
    ARGON2_TIME_COST: int = config("ARGON2_TIME_COST", default=2, cast=int)
    ARGON2_MEMORY_COST: int = config("ARGON2_MEMORY_COST", default=65536, cast=int)
    ARGON2_PARALLELISM: int = config("ARGON2_PARALLELISM", default=2, cast=int)

    # ----- SSH credential encryption -----
    SSH_ENCRYPTION_MASTER_KEY: str = config("SSH_ENCRYPTION_MASTER_KEY")
    SSH_CONNECTION_TIMEOUT: int = config("SSH_CONNECTION_TIMEOUT", default=10, cast=int)
    SSH_MAX_RETRY_LIMIT: int = config("SSH_MAX_RETRY_LIMIT", default=3, cast=int)

    # ----- Rate limiting -----
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = config(
        "RATE_LIMIT_LOGIN_MAX_ATTEMPTS", default=5, cast=int
    )
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = config(
        "RATE_LIMIT_LOGIN_WINDOW_SECONDS", default=60, cast=int
    )
    RATE_LIMIT_API_MAX_REQUESTS: int = config(
        "RATE_LIMIT_API_MAX_REQUESTS", default=100, cast=int
    )
    RATE_LIMIT_API_WINDOW_SECONDS: int = config(
        "RATE_LIMIT_API_WINDOW_SECONDS", default=60, cast=int
    )

    # ----- Session -----
    SESSION_INACTIVITY_TIMEOUT_MINUTES: int = config(
        "SESSION_INACTIVITY_TIMEOUT_MINUTES", default=30, cast=int
    )

    # ----- Cerebras AI -----
    CEREBRAS_API_KEY: str = config("CEREBRAS_API_KEY", default="")
    CEREBRAS_MODEL: str = config("CEREBRAS_MODEL", default="gpt-oss-120b")
    CEREBRAS_MAX_TOKENS: int = config("CEREBRAS_MAX_TOKENS", default=1000, cast=int)

    # ----- Redis & Celery -----
    REDIS_HOST: str = config("REDIS_HOST", default="localhost")
    REDIS_PORT: int = config("REDIS_PORT", default=6379, cast=int)
    REDIS_DB: int = config("REDIS_DB", default=0, cast=int)
    CELERY_BROKER_URL: str = config(
        "CELERY_BROKER_URL", default="redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND: str = config(
        "CELERY_RESULT_BACKEND", default="redis://localhost:6379/0"
    )

    # ----- Scheduler -----
    SCHEDULER_REPORT_INTERVAL_HOURS: int = config(
        "SCHEDULER_REPORT_INTERVAL_HOURS", default=24, cast=int
    )

    # ----- Data retention -----
    METRICS_RETENTION_DAYS: int = config("METRICS_RETENTION_DAYS", default=30, cast=int)
    LOGS_RETENTION_DAYS: int = config("LOGS_RETENTION_DAYS", default=14, cast=int)
    AI_REPORTS_RETENTION_DAYS: int = config(
        "AI_REPORTS_RETENTION_DAYS", default=90, cast=int
    )

    # ----- Email notifications (SMTP) -----
    SMTP_HOST: str = config("SMTP_HOST", default="")
    SMTP_PORT: int = config("SMTP_PORT", default=587, cast=int)
    SMTP_USERNAME: str = config("SMTP_USERNAME", default="")
    SMTP_PASSWORD: str = config("SMTP_PASSWORD", default="")
    SMTP_FROM_EMAIL: str = config("SMTP_FROM_EMAIL", default="")
    SMTP_TO_EMAIL: str = config("SMTP_TO_EMAIL", default="")
    SMTP_USE_TLS: bool = config("SMTP_USE_TLS", default=True, cast=bool)

    # ----- Intrusion detection -----
    INTRUSION_FAILED_LOGIN_THRESHOLD: int = config(
        "INTRUSION_FAILED_LOGIN_THRESHOLD", default=3, cast=int
    )
    INTRUSION_ALERT_WINDOW_MINUTES: int = config(
        "INTRUSION_ALERT_WINDOW_MINUTES", default=10, cast=int
    )

    # ----- Nginx & SSL -----
    NGINX_SERVER_NAME: str = config("NGINX_SERVER_NAME", default="")
    SSL_CERT_PATH: str = config("SSL_CERT_PATH", default="")
    SSL_KEY_PATH: str = config("SSL_KEY_PATH", default="")

    # ----- Deployment -----
    DEPLOYMENT_USER: str = config("DEPLOYMENT_USER", default="root")
    APP_DIR: str = config("APP_DIR", default=str(PROJECT_ROOT))
    ENV_FILE_PATH: str = config("ENV_FILE_PATH", default=str(ENV_PATH))

    # ----- Systemd services -----
    BACKEND_SERVICE_NAME: str = config("BACKEND_SERVICE_NAME", default="ai-infra-backend")
    FRONTEND_SERVICE_NAME: str = config(
        "FRONTEND_SERVICE_NAME", default="ai-infra-frontend"
    )

    # ----- Uptime monitoring -----
    UPTIME_MONITOR_URL: str = config("UPTIME_MONITOR_URL", default="")

    # ------------------------------------------------------------------
    # Derived connection URLs (built from discrete, correctly-filled vars)
    # ------------------------------------------------------------------
    @property
    def DATABASE_URL_ASYNC(self) -> URL:
        """SQLAlchemy URL object for the asyncpg driver (used by the app)."""
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            database=self.DATABASE_NAME,
        )

    @property
    def database_url_async_str(self) -> str:
        """Rendered async URL string with the password exposed for the driver."""
        return self.DATABASE_URL_ASYNC.render_as_string(hide_password=False)

    @property
    def CORS_ORIGINS(self) -> list[str]:
        origins = {self.FRONTEND_URL, self.APP_URL}
        origins.add(f"http://{self.FRONTEND_HOST}:{self.FRONTEND_PORT}")
        return [o for o in origins if o]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton accessor for application settings."""
    return Settings()


settings = get_settings()

"""
FastAPI application entry point for the AI Infrastructure Monitoring Dashboard.

Wires together:
  * startup env validation (fails fast if required .env vars are missing),
  * slowapi rate limiting (429 on excess) with Redis storage,
  * CORS restricted to the configured frontend origin,
  * the authentication router.

Run:  uvicorn main:app --host 127.0.0.1 --port 8002
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import settings
from middleware.rate_limit import limiter
from routers import auth as auth_router
from routers import dashboard as dashboard_router
from routers import metrics as metrics_router
from routers import servers as servers_router
from utils.security_check import verify_required_env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_infra")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast at startup if configuration is incomplete.
    verify_required_env()
    logger.info("Environment validation passed; starting %s", settings.APP_NAME)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
)

# --- Rate limiting (slowapi) ---
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return a clear 429 message when a rate limit is exceeded."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Rate limit exceeded. Please slow down and try again shortly.",
            "limit": str(exc.detail),
        },
    )


app.add_middleware(SlowAPIMiddleware)

# --- CORS (restricted to configured frontend origins) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth_router.router)
app.include_router(servers_router.router)
app.include_router(dashboard_router.router)
app.include_router(metrics_router.router)


@app.get("/health", tags=["health"])
@limiter.exempt
async def health() -> dict:
    """Lightweight liveness probe (used by uptime monitoring)."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/", tags=["health"])
@limiter.exempt
async def root() -> dict:
    return {"message": f"{settings.APP_NAME} API", "docs": "/docs"}

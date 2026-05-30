"""
Celery application.

Broker/backend come from .env. Tasks live in ``tasks.metric_tasks`` and are
included here so the worker (``celery -A celery_app worker``) registers them.
"""
from celery import Celery

from config import settings

celery_app = Celery(
    "ai_infra",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.metric_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=100,
    result_expires=3600,
)

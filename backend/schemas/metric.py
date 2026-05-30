"""Pydantic schemas for server metrics."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    server_id: uuid.UUID
    cpu_usage: float | None
    ram_usage: float | None
    disk_usage: float | None
    uptime: str | None
    running_processes: Any | None
    open_ports: Any | None
    network_stats: Any | None
    collected_at: datetime


class MetricHistoryPoint(BaseModel):
    """Lightweight point for time-series charts."""
    collected_at: datetime
    cpu_usage: float | None
    ram_usage: float | None
    disk_usage: float | None


class MetricHistoryResponse(BaseModel):
    server_id: uuid.UUID
    hours: int
    points: list[MetricHistoryPoint]


class RefreshResponse(BaseModel):
    success: bool
    message: str
    metric: MetricOut | None = None


class RefreshDispatchResponse(BaseModel):
    """Returned when a manual refresh is queued as a Celery task."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    state: str            # PENDING / STARTED / SUCCESS / FAILURE / RETRY
    ready: bool
    successful: bool | None = None
    result: dict | None = None

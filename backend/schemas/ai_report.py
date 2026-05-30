"""Pydantic schemas for AI report endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from models.enums import ReportType


class AIReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    server_id: uuid.UUID
    summary: str | None
    risk_score: int | None
    risk_level: str | None
    key_findings: Any | None
    recommended_actions: Any | None
    security_observations: Any | None
    performance_observations: Any | None
    report_type: ReportType
    generated_at: datetime


class AIReportHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    risk_score: int | None
    risk_level: str | None
    report_type: ReportType
    generated_at: datetime


class AIReportHistoryPage(BaseModel):
    items: list[AIReportHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class GenerateResponse(BaseModel):
    task_id: str
    status: str
    message: str

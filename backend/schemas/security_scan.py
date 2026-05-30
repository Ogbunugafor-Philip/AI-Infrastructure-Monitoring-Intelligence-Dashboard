"""Pydantic schemas for security scans."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SecurityScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    server_id: uuid.UUID
    scan_results: Any | None
    total_checks: int
    passed: int
    warnings: int
    critical_findings: int
    overall_score: int
    scanned_at: datetime
    scanned_by_user_id: uuid.UUID | None


class SecurityScanHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    total_checks: int
    passed: int
    warnings: int
    critical_findings: int
    overall_score: int
    scanned_at: datetime


class SecurityScanHistoryPage(BaseModel):
    items: list[SecurityScanHistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int

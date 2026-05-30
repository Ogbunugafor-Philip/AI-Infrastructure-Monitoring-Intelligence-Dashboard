"""Pydantic schemas for dashboard aggregation endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from models.enums import ServerStatus, SSHAuthMethod

Severity = Literal["high", "medium", "low"]


class OverviewResponse(BaseModel):
    total_servers: int
    servers_online: int
    servers_offline: int
    servers_warning: int
    avg_cpu_usage: float
    avg_ram_usage: float
    avg_disk_usage: float
    security_alerts_24h: int
    audit_events_24h: int


class ServerStatusItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    ip_address: str
    ssh_port: int
    ssh_username: str
    ssh_auth_method: SSHAuthMethod
    ssh_key_only_mode: bool
    status: ServerStatus
    cpu_usage: float | None = None
    ram_usage: float | None = None
    disk_usage: float | None = None
    uptime: str | None = None
    last_updated: datetime | None = None


class SecurityAlert(BaseModel):
    id: uuid.UUID
    event_type: str
    event_description: str | None
    ip_address: str | None
    user_id: uuid.UUID | None
    target_server_id: uuid.UUID | None
    success: bool
    severity: Severity
    created_at: datetime


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    event_type: str
    event_description: str | None
    ip_address: str | None
    target_server_id: uuid.UUID | None
    success: bool
    created_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int

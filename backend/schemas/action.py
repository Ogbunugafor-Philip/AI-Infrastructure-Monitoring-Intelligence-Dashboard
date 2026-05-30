"""Pydantic schemas for privileged action endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.enums import ActionStatus, RiskLevel


class CommandItem(BaseModel):
    command_key: str
    description: str
    risk_level: str
    command_string: str


class CommandCatalog(BaseModel):
    low: list[CommandItem]
    medium: list[CommandItem]
    high: list[CommandItem]


class DryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_id: uuid.UUID
    command_key: str = Field(min_length=1, max_length=100)


class DryRunResponse(BaseModel):
    server_ip: str
    command_key: str
    exact_command_string: str
    output: str
    executed_at: datetime


class ActionRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_id: uuid.UUID
    command_key: str = Field(min_length=1, max_length=100)


class PasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dashboard_password: str = Field(min_length=1)


class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    server_id: uuid.UUID
    server_ip: str | None = None
    server_name: str | None = None
    requested_by_user_id: uuid.UUID | None
    confirmed_by_user_id: uuid.UUID | None
    command_key: str
    command_string: str
    risk_level: RiskLevel
    status: ActionStatus
    dry_run_output: str | None
    execution_output: str | None
    password_verified: bool
    second_confirmation_required: bool
    second_confirmation_received: bool
    time_lock_expires_at: datetime | None
    executed_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_model(cls, action, server=None) -> "ActionOut":
        out = cls.model_validate(action)
        if server is not None:
            out.server_ip = server.ip_address
            out.server_name = server.name
        return out


class ActionHistoryPage(BaseModel):
    items: list[ActionOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class EmergencyKillResponse(BaseModel):
    server_id: uuid.UUID
    credentials_revoked: bool
    actions_cancelled: int
    connections_terminated: int
    status: str
    message: str

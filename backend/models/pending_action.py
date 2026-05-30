"""Pending privileged action — the lifecycle record for a whitelisted command."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from models.enums import ActionStatus, RiskLevel


class PendingAction(Base):
    __tablename__ = "pending_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    command_key: Mapped[str] = mapped_column(String(100), nullable=False)
    command_string: Mapped[str] = mapped_column(String, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level"), nullable=False, index=True
    )
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status"),
        nullable=False, default=ActionStatus.pending, index=True,
    )
    dry_run_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    second_confirmation_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    second_confirmation_received: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

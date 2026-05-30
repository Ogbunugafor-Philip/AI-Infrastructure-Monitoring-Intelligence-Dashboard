"""Persistent rate-limit / lockout tracking per IP + endpoint."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class RateLimitTracking(Base):
    __tablename__ = "rate_limit_tracking"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

"""Collected server log entries (raw line stored AES-256-GCM encrypted)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    log_source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    log_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Encrypted (AES-256-GCM) raw log line — never stored in plaintext.
    raw_line: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

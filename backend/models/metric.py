"""Per-server collected metrics model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    cpu_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_usage: Mapped[float | None] = mapped_column(Float, nullable=True)
    uptime: Mapped[str | None] = mapped_column(String, nullable=True)
    running_processes: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    open_ports: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    network_stats: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    server: Mapped["Server"] = relationship(back_populates="metrics")  # noqa: F821

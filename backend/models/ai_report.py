"""AI-generated server health/risk report model."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import ReportType


class AIReport(Base):
    __tablename__ = "ai_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_actions: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    # Encrypted (AES-256-GCM) snapshot of the raw data the report was built from.
    raw_data_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType, name="report_type"), nullable=False, default=ReportType.manual
    )

    __table_args__ = (
        CheckConstraint("risk_score >= 1 AND risk_score <= 10", name="ck_risk_score_range"),
    )

    server: Mapped["Server"] = relationship(back_populates="ai_reports")  # noqa: F821

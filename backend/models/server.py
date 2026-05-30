"""Monitored server model."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.enums import ServerStatus, SSHAuthMethod


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22, nullable=False)
    ssh_username: Mapped[str] = mapped_column(String(255), nullable=False)
    ssh_auth_method: Mapped[SSHAuthMethod] = mapped_column(
        Enum(SSHAuthMethod, name="ssh_auth_method"), nullable=False
    )
    # Stored encrypted at rest (AES-256-GCM) — never plaintext.
    encrypted_ssh_password: Mapped[str | None] = mapped_column(String, nullable=True)
    encrypted_ssh_key: Mapped[str | None] = mapped_column(String, nullable=True)
    ssh_key_only_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_ip_whitelist: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ServerStatus] = mapped_column(
        Enum(ServerStatus, name="server_status"), default=ServerStatus.offline, nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    creator: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="servers", foreign_keys=[created_by]
    )
    metrics: Mapped[list["Metric"]] = relationship(  # noqa: F821
        back_populates="server", cascade="all, delete-orphan"
    )
    ai_reports: Mapped[list["AIReport"]] = relationship(  # noqa: F821
        back_populates="server", cascade="all, delete-orphan"
    )

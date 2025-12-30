"""Voice profile model."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VoiceProfileStatus(str, PyEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VoiceProfile(Base):
    """Voice profile model."""

    __tablename__ = "voice_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    elevenlabs_voice_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[VoiceProfileStatus] = mapped_column(
        Enum(VoiceProfileStatus), default=VoiceProfileStatus.PROCESSING
    )
    sample_urls: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    sample_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="voice_profiles")

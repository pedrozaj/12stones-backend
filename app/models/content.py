"""Content models."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ContentType(str, PyEnum):
    PHOTO = "photo"
    VIDEO = "video"


class ContentSource(str, PyEnum):
    UPLOAD = "upload"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"


class ContentStatus(str, PyEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ContentItem(Base):
    """Content item model."""

    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    type: Mapped[ContentType] = mapped_column(Enum(ContentType), nullable=False)
    source: Mapped[ContentSource] = mapped_column(Enum(ContentSource), nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), default=ContentStatus.PROCESSING
    )
    r2_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_r2_key: Mapped[str | None] = mapped_column(String(500))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    original_caption: Mapped[str | None] = mapped_column(Text)
    custom_caption: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_id: Mapped[str | None] = mapped_column(String(255))
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location_name: Mapped[str | None] = mapped_column(String(255))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    included_in_narrative: Mapped[bool] = mapped_column(Boolean, default=True)
    narrative_order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="content_items")
    analysis: Mapped["ContentAnalysis"] = relationship(back_populates="content_item", uselist=False)


class ContentAnalysis(Base):
    """Content analysis results."""

    __tablename__ = "content_analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id"), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detected_objects: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    detected_people_count: Mapped[int | None] = mapped_column(Integer)
    detected_text: Mapped[str | None] = mapped_column(Text)
    scene_type: Mapped[str | None] = mapped_column(String(100))
    sentiment: Mapped[str | None] = mapped_column(String(50))
    sentiment_score: Mapped[float | None] = mapped_column(Numeric(3, 2))
    narrative_importance: Mapped[float | None] = mapped_column(Numeric(3, 2))
    suggested_narrative_text: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    model_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    content_item: Mapped["ContentItem"] = relationship(back_populates="analysis")

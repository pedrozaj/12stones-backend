"""Project models."""

import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectStatus(str, PyEnum):
    """Project status enum."""

    DRAFT = "draft"
    IMPORTING = "importing"
    ANALYZING = "analyzing"
    GENERATING_NARRATIVE = "generating_narrative"
    GENERATING_AUDIO = "generating_audio"
    RENDERING = "rendering"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base):
    """Project model."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False
    )
    timeframe_start: Mapped[date] = mapped_column(Date, nullable=False)
    timeframe_end: Mapped[date] = mapped_column(Date, nullable=False)
    voice_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voice_profiles.id"), nullable=True
    )
    current_narrative_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    current_video_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="projects")
    settings: Mapped["ProjectSettings"] = relationship(back_populates="project", uselist=False)
    content_items: Mapped[list["ContentItem"]] = relationship(back_populates="project")
    narratives: Mapped[list["Narrative"]] = relationship(back_populates="project")
    videos: Mapped[list["Video"]] = relationship(back_populates="project")


class ProjectSettings(Base):
    """Project settings model."""

    __tablename__ = "project_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), unique=True, nullable=False
    )
    music_style: Mapped[str] = mapped_column(String(50), default="cinematic")
    music_track_id: Mapped[str | None] = mapped_column(String(255))
    transition_style: Mapped[str] = mapped_column(String(50), default="smooth")
    narrative_tone: Mapped[str] = mapped_column(String(50), default="reflective")
    video_resolution: Mapped[str] = mapped_column(String(10), default="1080p")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="settings")

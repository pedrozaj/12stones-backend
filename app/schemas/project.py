"""Project schemas."""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ProjectStatus(str, Enum):
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


class ProjectSettings(BaseModel):
    """Project settings."""

    music_style: str = "cinematic"
    music_track_id: str | None = None
    transition_style: str = "smooth"
    narrative_tone: str = "reflective"


class ProjectCreate(BaseModel):
    """Create project request."""

    title: str
    timeframe_start: date
    timeframe_end: date
    settings: ProjectSettings | None = None


class ProjectUpdate(BaseModel):
    """Update project request."""

    title: str | None = None
    timeframe_start: date | None = None
    timeframe_end: date | None = None
    settings: ProjectSettings | None = None
    voice_profile_id: UUID | None = None
    current_narrative_id: UUID | None = None


class ProjectResponse(BaseModel):
    """Project response model."""

    id: UUID
    title: str
    status: ProjectStatus
    timeframe_start: date
    timeframe_end: date
    settings: ProjectSettings | None = None
    content_count: int = 0
    voice_profile_id: UUID | None = None
    current_narrative_id: UUID | None = None
    current_video_id: UUID | None = None
    thumbnail_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

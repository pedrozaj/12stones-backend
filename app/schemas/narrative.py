"""Narrative schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class NarrativeStatus(str, Enum):
    """Narrative status enum."""

    GENERATING = "generating"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"


class NarrativeScene(BaseModel):
    """A scene in the narrative."""

    id: str
    order: int
    text: str
    content_ids: list[UUID]
    duration_seconds: int
    transition: str = "fade"


class NarrativeResponse(BaseModel):
    """Narrative response model."""

    id: UUID
    version: int
    status: NarrativeStatus
    script: str | None = None
    scenes: list[NarrativeScene] = []
    word_count: int | None = None
    estimated_duration: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NarrativeRegenerateRequest(BaseModel):
    """Regenerate narrative request."""

    tone: str | None = None
    focus_content_ids: list[UUID] | None = None
    exclude_content_ids: list[UUID] | None = None

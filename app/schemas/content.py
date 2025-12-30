"""Content schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ContentType(str, Enum):
    """Content type enum."""

    PHOTO = "photo"
    VIDEO = "video"


class ContentSource(str, Enum):
    """Content source enum."""

    UPLOAD = "upload"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"


class ContentAnalysis(BaseModel):
    """Content analysis results."""

    description: str
    detected_objects: list[str] = []
    sentiment: str | None = None


class ContentItemResponse(BaseModel):
    """Content item response model."""

    id: UUID
    type: ContentType
    source: ContentSource
    thumbnail_url: str | None = None
    original_url: str | None = None
    caption: str | None = None
    taken_at: datetime | None = None
    location: str | None = None
    analysis: ContentAnalysis | None = None
    included_in_narrative: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentUpdate(BaseModel):
    """Update content request."""

    included_in_narrative: bool | None = None
    custom_caption: str | None = None


class ImportRequest(BaseModel):
    """Import content request."""

    sources: list[ContentSource]
    date_range: dict[str, str] | None = None  # {"start": "2024-01-01", "end": "2024-12-31"}

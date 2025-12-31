"""Voice profile schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class VoiceProfileStatus(str, Enum):
    """Voice profile status enum."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VoiceProfileCreate(BaseModel):
    """Create voice profile request."""

    name: str


class VoiceProfileResponse(BaseModel):
    """Voice profile response model."""

    id: UUID
    name: str
    status: VoiceProfileStatus
    sample_duration: int | None = None
    sample_urls: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class VoicePreviewRequest(BaseModel):
    """Voice preview request."""

    text: str

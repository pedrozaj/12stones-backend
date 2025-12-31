"""Video schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class VideoStatus(str, Enum):
    """Video status enum."""

    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoResolution(str, Enum):
    """Video resolution enum."""

    HD = "720p"
    FHD = "1080p"
    UHD = "4k"


class VideoResponse(BaseModel):
    """Video response model."""

    id: UUID
    narrative_id: UUID
    status: VideoStatus
    resolution: VideoResolution
    duration: int | None = None
    file_size: int | None = None
    download_url: str | None = None
    render_progress: int = 0
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoRenderRequest(BaseModel):
    """Video render request."""

    narrative_id: UUID
    voice_profile_id: UUID
    resolution: VideoResolution = VideoResolution.FHD
    music_track: str | None = None

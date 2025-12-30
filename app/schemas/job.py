"""Job schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class JobType(str, Enum):
    """Job type enum."""

    CONTENT_IMPORT = "content:import"
    CONTENT_ANALYZE = "content:analyze"
    VOICE_CLONE = "voice:clone"
    NARRATIVE_GENERATE = "narrative:generate"
    AUDIO_SYNTHESIZE = "audio:synthesize"
    VIDEO_RENDER = "video:render"


class JobStatus(str, Enum):
    """Job status enum."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobResponse(BaseModel):
    """Job response model."""

    id: UUID
    type: JobType
    status: JobStatus
    progress: int = 0
    project_id: UUID | None = None
    started_at: datetime | None = None
    estimated_completion: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}

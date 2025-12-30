"""Social connection schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class SocialPlatform(str, Enum):
    """Supported social platforms."""

    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"


class SocialConnectionResponse(BaseModel):
    """Social connection response model."""

    id: UUID
    platform: SocialPlatform
    username: str | None = None
    connected_at: datetime
    last_sync: datetime | None = None

    model_config = {"from_attributes": True}

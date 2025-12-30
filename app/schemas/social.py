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
    platform_username: str | None = None
    connected_at: datetime
    last_sync: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to map model fields to schema fields."""
        return cls(
            id=obj.id,
            platform=obj.platform,
            platform_username=obj.username,
            connected_at=obj.created_at,
            last_sync=obj.last_sync_at,
        )

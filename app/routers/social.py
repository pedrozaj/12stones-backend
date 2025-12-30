"""Social media connection endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.social import SocialConnectionResponse

router = APIRouter()


@router.get("/connections", response_model=list[SocialConnectionResponse])
async def list_connections(db: Session = Depends(get_db)):
    """List user's connected social accounts."""
    # TODO: Implement list connections
    return []


@router.get("/connect/{platform}")
async def connect_platform(platform: str):
    """Initiate OAuth flow for a platform."""
    valid_platforms = ["instagram", "facebook", "tiktok"]
    if platform not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")

    # TODO: Implement OAuth redirect
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/callback/{platform}")
async def oauth_callback(platform: str, code: str, state: str | None = None):
    """Handle OAuth callback from platform."""
    # TODO: Implement OAuth callback
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/connections/{connection_id}")
async def disconnect_platform(connection_id: UUID, db: Session = Depends(get_db)):
    """Disconnect a social account."""
    # TODO: Implement disconnect
    return {"data": {"success": True}}


@router.post("/connections/{connection_id}/sync")
async def sync_connection(connection_id: UUID, db: Session = Depends(get_db)):
    """Trigger content sync from connected account."""
    # TODO: Implement sync trigger
    raise HTTPException(status_code=501, detail="Not implemented")

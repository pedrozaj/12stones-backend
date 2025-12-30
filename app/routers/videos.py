"""Video endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.video import VideoRenderRequest, VideoResponse

router = APIRouter()


@router.get("", response_model=list[VideoResponse])
async def list_videos(project_id: UUID, db: Session = Depends(get_db)):
    """List video renders for a project."""
    # TODO: Implement list videos
    return []


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    project_id: UUID,
    video_id: UUID,
    db: Session = Depends(get_db),
):
    """Get video details."""
    # TODO: Implement get video
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/render")
async def render_video(
    project_id: UUID,
    request: VideoRenderRequest,
    db: Session = Depends(get_db),
):
    """Start video rendering."""
    # TODO: Implement video render trigger
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{video_id}/download")
async def download_video(
    project_id: UUID,
    video_id: UUID,
    db: Session = Depends(get_db),
):
    """Get signed download URL for video."""
    # TODO: Implement download URL generation
    raise HTTPException(status_code=501, detail="Not implemented")

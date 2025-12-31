"""Video endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.narrative import Narrative
from app.models.project import Project
from app.models.user import User
from app.models.video import Video, VideoResolution, VideoStatus
from app.models.voice import VoiceProfile
from app.routers.auth import get_current_user_from_token
from app.schemas.video import VideoRenderRequest, VideoResponse
from app.utils.storage import get_file_url
from app.workers.video_tasks import render_video

router = APIRouter()


@router.get("", response_model=list[VideoResponse])
async def list_videos(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """List video renders for a project."""
    # Verify project access
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    videos = db.query(Video).filter(
        Video.project_id == project_id,
    ).order_by(Video.created_at.desc()).all()

    result = []
    for video in videos:
        download_url = None
        if video.r2_key and video.status == VideoStatus.COMPLETED:
            download_url = get_file_url(video.r2_key)

        result.append(VideoResponse(
            id=video.id,
            narrative_id=video.narrative_id,
            status=video.status,
            resolution=video.resolution,
            duration=video.duration_seconds,
            file_size=video.file_size_bytes,
            download_url=download_url,
            render_progress=video.render_progress,
            error_message=video.error_message,
            created_at=video.created_at,
        ))

    return result


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    project_id: UUID,
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Get video details."""
    # Verify project access
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    video = db.query(Video).filter(
        Video.id == video_id,
        Video.project_id == project_id,
    ).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    download_url = None
    if video.r2_key and video.status == VideoStatus.COMPLETED:
        download_url = get_file_url(video.r2_key)

    return VideoResponse(
        id=video.id,
        narrative_id=video.narrative_id,
        status=video.status,
        resolution=video.resolution,
        duration=video.duration_seconds,
        file_size=video.file_size_bytes,
        download_url=download_url,
        render_progress=video.render_progress,
        error_message=video.error_message,
        created_at=video.created_at,
    )


@router.post("/render", response_model=VideoResponse)
async def start_video_render(
    project_id: UUID,
    request: VideoRenderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Start video rendering."""
    # Verify project access
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify narrative exists and belongs to project
    narrative = db.query(Narrative).filter(
        Narrative.id == request.narrative_id,
        Narrative.project_id == project_id,
    ).first()

    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Verify voice profile exists and belongs to user
    voice_profile = db.query(VoiceProfile).filter(
        VoiceProfile.id == request.voice_profile_id,
        VoiceProfile.user_id == current_user.id,
    ).first()

    if not voice_profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # Create video record
    video = Video(
        project_id=project_id,
        narrative_id=request.narrative_id,
        voice_profile_id=request.voice_profile_id,
        resolution=VideoResolution(request.resolution.value),
        status=VideoStatus.QUEUED,
        music_track_id=request.music_track,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # Update project's current video
    project.current_video_id = video.id
    db.commit()

    # Queue the render task
    render_video.delay(str(video.id))

    return VideoResponse(
        id=video.id,
        narrative_id=video.narrative_id,
        status=video.status,
        resolution=video.resolution,
        duration=None,
        file_size=None,
        download_url=None,
        render_progress=0,
        error_message=None,
        created_at=video.created_at,
    )


@router.get("/{video_id}/download")
async def download_video(
    project_id: UUID,
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Get signed download URL for video."""
    # Verify project access
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    video = db.query(Video).filter(
        Video.id == video_id,
        Video.project_id == project_id,
    ).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.status != VideoStatus.COMPLETED or not video.r2_key:
        raise HTTPException(status_code=400, detail="Video not ready for download")

    download_url = get_file_url(video.r2_key)

    return {"download_url": download_url}

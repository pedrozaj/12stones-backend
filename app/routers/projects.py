"""Project endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project, ProjectSettings as ProjectSettingsModel, ProjectStatus
from app.models.user import User
from app.routers.auth import get_current_user_from_token
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """List user's projects."""
    query = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    )
    if status:
        query = query.filter(Project.status == status)

    projects = query.order_by(Project.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    # Convert to response format with content count
    result = []
    for project in projects:
        content_count = len(project.content_items) if project.content_items else 0
        result.append(ProjectResponse(
            id=project.id,
            title=project.title,
            status=project.status,
            timeframe_start=project.timeframe_start,
            timeframe_end=project.timeframe_end,
            content_count=content_count,
            voice_profile_id=project.voice_profile_id,
            current_narrative_id=project.current_narrative_id,
            current_video_id=project.current_video_id,
            thumbnail_url=project.thumbnail_url,
            created_at=project.created_at,
        ))
    return result


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Create a new project."""
    project = Project(
        user_id=current_user.id,
        title=request.title,
        timeframe_start=request.timeframe_start,
        timeframe_end=request.timeframe_end,
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        timeframe_start=project.timeframe_start,
        timeframe_end=project.timeframe_end,
        content_count=0,
        voice_profile_id=project.voice_profile_id,
        current_narrative_id=project.current_narrative_id,
        current_video_id=project.current_video_id,
        thumbnail_url=project.thumbnail_url,
        created_at=project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Get project details."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content_count = len(project.content_items) if project.content_items else 0

    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        timeframe_start=project.timeframe_start,
        timeframe_end=project.timeframe_end,
        content_count=content_count,
        voice_profile_id=project.voice_profile_id,
        current_narrative_id=project.current_narrative_id,
        current_video_id=project.current_video_id,
        thumbnail_url=project.thumbnail_url,
        created_at=project.created_at,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Update project details."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields if provided
    if request.title is not None:
        project.title = request.title
    if request.timeframe_start is not None:
        project.timeframe_start = request.timeframe_start
    if request.timeframe_end is not None:
        project.timeframe_end = request.timeframe_end
    if request.voice_profile_id is not None:
        project.voice_profile_id = request.voice_profile_id

    db.commit()
    db.refresh(project)

    content_count = len(project.content_items) if project.content_items else 0

    return ProjectResponse(
        id=project.id,
        title=project.title,
        status=project.status,
        timeframe_start=project.timeframe_start,
        timeframe_end=project.timeframe_end,
        content_count=content_count,
        voice_profile_id=project.voice_profile_id,
        current_narrative_id=project.current_narrative_id,
        current_video_id=project.current_video_id,
        thumbnail_url=project.thumbnail_url,
        created_at=project.created_at,
    )


@router.delete("/{project_id}")
async def delete_project(project_id: UUID, db: Session = Depends(get_db)):
    """Delete a project."""
    # TODO: Implement delete project
    return {"data": {"success": True}}


@router.post("/{project_id}/generate")
async def generate_video(project_id: UUID, db: Session = Depends(get_db)):
    """Start video generation for project."""
    # TODO: Implement video generation trigger
    raise HTTPException(status_code=501, detail="Not implemented")

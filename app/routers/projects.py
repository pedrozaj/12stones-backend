"""Project endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List user's projects."""
    # TODO: Implement list projects
    return []


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(request: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project."""
    # TODO: Implement create project
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: Session = Depends(get_db)):
    """Get project details."""
    # TODO: Implement get project
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    db: Session = Depends(get_db),
):
    """Update project details."""
    # TODO: Implement update project
    raise HTTPException(status_code=501, detail="Not implemented")


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

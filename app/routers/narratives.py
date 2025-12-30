"""Narrative endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.narrative import NarrativeRegenerateRequest, NarrativeResponse

router = APIRouter()


@router.get("", response_model=list[NarrativeResponse])
async def list_narratives(project_id: UUID, db: Session = Depends(get_db)):
    """List narratives for a project."""
    # TODO: Implement list narratives
    return []


@router.get("/{narrative_id}", response_model=NarrativeResponse)
async def get_narrative(
    project_id: UUID,
    narrative_id: UUID,
    db: Session = Depends(get_db),
):
    """Get full narrative with script."""
    # TODO: Implement get narrative
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/regenerate")
async def regenerate_narrative(
    project_id: UUID,
    request: NarrativeRegenerateRequest,
    db: Session = Depends(get_db),
):
    """Regenerate the narrative with different parameters."""
    # TODO: Implement narrative regeneration
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{narrative_id}/approve")
async def approve_narrative(
    project_id: UUID,
    narrative_id: UUID,
    db: Session = Depends(get_db),
):
    """Approve a narrative for video generation."""
    # TODO: Implement narrative approval
    raise HTTPException(status_code=501, detail="Not implemented")

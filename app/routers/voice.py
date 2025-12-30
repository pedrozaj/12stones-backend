"""Voice profile endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.voice import VoicePreviewRequest, VoiceProfileCreate, VoiceProfileResponse

router = APIRouter()


@router.get("/profiles", response_model=list[VoiceProfileResponse])
async def list_voice_profiles(db: Session = Depends(get_db)):
    """List user's voice profiles."""
    # TODO: Implement list profiles
    return []


@router.post("/profiles", response_model=VoiceProfileResponse, status_code=201)
async def create_voice_profile(
    name: str,
    samples: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Create a new voice profile from audio samples."""
    # TODO: Implement voice clone creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/profiles/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(profile_id: UUID, db: Session = Depends(get_db)):
    """Get voice profile details."""
    # TODO: Implement get profile
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/profiles/{profile_id}")
async def delete_voice_profile(profile_id: UUID, db: Session = Depends(get_db)):
    """Delete voice profile and all associated data."""
    # TODO: Implement delete profile
    return {"data": {"success": True}}


@router.post("/profiles/{profile_id}/preview")
async def preview_voice(
    profile_id: UUID,
    request: VoicePreviewRequest,
    db: Session = Depends(get_db),
):
    """Generate a preview with the voice profile."""
    # TODO: Implement voice preview
    raise HTTPException(status_code=501, detail="Not implemented")

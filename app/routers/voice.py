"""Voice profile endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.voice import VoiceProfile, VoiceProfileStatus
from app.routers.auth import get_current_user_from_token
from app.schemas.voice import VoicePreviewRequest, VoiceProfileCreate, VoiceProfileResponse
from app.utils.storage import upload_file_to_r2, get_file_url

router = APIRouter()


@router.get("/profiles", response_model=list[VoiceProfileResponse])
async def list_voice_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """List user's voice profiles."""
    profiles = db.query(VoiceProfile).filter(
        VoiceProfile.user_id == current_user.id,
        VoiceProfile.deleted_at.is_(None),
    ).order_by(VoiceProfile.created_at.desc()).all()

    return [
        VoiceProfileResponse(
            id=p.id,
            name=p.name,
            status=p.status,
            sample_duration=p.sample_duration_seconds,
            created_at=p.created_at,
        )
        for p in profiles
    ]


@router.post("/profiles", response_model=VoiceProfileResponse, status_code=201)
async def create_voice_profile(
    name: str = Form(...),
    samples: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Create a new voice profile from audio samples."""
    if len(samples) == 0:
        raise HTTPException(status_code=400, detail="At least one audio sample is required")

    # Upload each sample to R2
    sample_urls = []
    total_size = 0

    for i, sample in enumerate(samples):
        content = await sample.read()
        total_size += len(content)

        # Upload to R2 in voice-samples folder
        key = upload_file_to_r2(
            file_data=content,
            filename=sample.filename or f"sample_{i}.webm",
            content_type=sample.content_type or "audio/webm",
            folder="voice-samples",
        )
        sample_urls.append(key)

    # Estimate duration based on file size (rough estimate: ~12KB per second for webm audio)
    estimated_duration = total_size // 12000

    # Create voice profile record
    # Status is READY for now - when ElevenLabs integration is added, it will start as PROCESSING
    profile = VoiceProfile(
        user_id=current_user.id,
        name=name,
        status=VoiceProfileStatus.READY,
        sample_urls=sample_urls,
        sample_duration_seconds=estimated_duration if estimated_duration > 0 else None,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return VoiceProfileResponse(
        id=profile.id,
        name=profile.name,
        status=profile.status,
        sample_duration=profile.sample_duration_seconds,
        created_at=profile.created_at,
    )


@router.get("/profiles/{profile_id}", response_model=VoiceProfileResponse)
async def get_voice_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Get voice profile details."""
    profile = db.query(VoiceProfile).filter(
        VoiceProfile.id == profile_id,
        VoiceProfile.user_id == current_user.id,
        VoiceProfile.deleted_at.is_(None),
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    return VoiceProfileResponse(
        id=profile.id,
        name=profile.name,
        status=profile.status,
        sample_duration=profile.sample_duration_seconds,
        created_at=profile.created_at,
    )


@router.delete("/profiles/{profile_id}")
async def delete_voice_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Delete voice profile and all associated data."""
    from datetime import datetime

    profile = db.query(VoiceProfile).filter(
        VoiceProfile.id == profile_id,
        VoiceProfile.user_id == current_user.id,
        VoiceProfile.deleted_at.is_(None),
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    # Soft delete
    profile.deleted_at = datetime.utcnow()
    db.commit()

    return {"success": True}


@router.post("/profiles/{profile_id}/preview")
async def preview_voice(
    profile_id: UUID,
    request: VoicePreviewRequest,
    db: Session = Depends(get_db),
):
    """Generate a preview with the voice profile."""
    # TODO: Implement voice preview
    raise HTTPException(status_code=501, detail="Not implemented")

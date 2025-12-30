"""Narrative endpoints."""

import uuid
from datetime import datetime
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.content import ContentItem
from app.models.narrative import Narrative, NarrativeStatus
from app.models.project import Project
from app.models.user import User
from app.routers.auth import get_current_user_from_token
from app.schemas.narrative import NarrativeRegenerateRequest, NarrativeResponse, NarrativeScene
from app.utils.storage import get_file_url

router = APIRouter()
settings = get_settings()


def generate_narrative_with_claude(
    project_title: str,
    content_items: list[ContentItem],
    tone: str | None = None,
) -> dict:
    """Generate a narrative script using Claude AI."""

    # Build content descriptions
    content_descriptions = []
    for i, item in enumerate(content_items, 1):
        desc = f"{i}. "
        if item.type.value == "photo":
            desc += "[Photo] "
        else:
            desc += "[Video] "

        if item.original_caption:
            desc += f"Caption: {item.original_caption[:200]}"
        if item.taken_at:
            desc += f" (Taken: {item.taken_at.strftime('%B %d, %Y')})"
        if item.location_name:
            desc += f" Location: {item.location_name}"

        content_descriptions.append(desc)

    content_list = "\n".join(content_descriptions)

    tone_instruction = ""
    if tone:
        tone_instruction = f"\nTone: {tone}"

    prompt = f"""You are creating a heartfelt narrative script for a memorial video called "{project_title}".

The video will feature the following {len(content_items)} photos and videos:

{content_list}

Create a warm, personal narrative script that:
1. Tells a cohesive story connecting these memories
2. Is suitable for voiceover narration (2-3 minutes when read aloud)
3. References specific moments from the content where appropriate
4. Evokes emotion while celebrating the memories
5. Has a clear beginning, middle, and end
{tone_instruction}

Format your response as follows:
1. First, write the complete narrative script (aim for 300-500 words)
2. Then, break it into scenes. For each scene, specify:
   - The scene text (1-3 sentences)
   - Which content items (by number) should be shown
   - Suggested duration in seconds (5-15 seconds per scene)

Use this exact format for scenes:
---SCENES---
SCENE 1: [text] | CONTENT: [1,2] | DURATION: [8]
SCENE 2: [text] | CONTENT: [3] | DURATION: [6]
(and so on)

Write the narrative now:"""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # Parse the response
    script_text = response_text
    scenes = []

    if "---SCENES---" in response_text:
        parts = response_text.split("---SCENES---")
        script_text = parts[0].strip()
        scenes_text = parts[1].strip() if len(parts) > 1 else ""

        # Parse scenes
        for line in scenes_text.split("\n"):
            line = line.strip()
            if line.startswith("SCENE"):
                try:
                    # Parse: SCENE N: [text] | CONTENT: [1,2] | DURATION: [8]
                    scene_part = line.split(":", 1)[1] if ":" in line else line
                    parts = scene_part.split("|")

                    text = parts[0].strip() if len(parts) > 0 else ""

                    content_ids = []
                    duration = 8

                    for part in parts[1:]:
                        part = part.strip()
                        if part.startswith("CONTENT:"):
                            # Extract numbers from [1,2,3]
                            nums_str = part.replace("CONTENT:", "").strip().strip("[]")
                            content_ids = [int(n.strip()) for n in nums_str.split(",") if n.strip().isdigit()]
                        elif part.startswith("DURATION:"):
                            dur_str = part.replace("DURATION:", "").strip().strip("[]")
                            duration = int(dur_str) if dur_str.isdigit() else 8

                    if text:
                        scenes.append({
                            "text": text,
                            "content_indices": content_ids,
                            "duration": duration,
                        })
                except Exception:
                    continue

    # Calculate word count and duration
    word_count = len(script_text.split())
    # Average speaking rate is about 150 words per minute
    estimated_duration = int((word_count / 150) * 60)

    return {
        "script_text": script_text,
        "scenes": scenes,
        "word_count": word_count,
        "estimated_duration": estimated_duration,
    }


@router.get("", response_model=list[NarrativeResponse])
async def list_narratives(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """List narratives for a project."""
    narratives = db.query(Narrative).filter(
        Narrative.project_id == project_id,
    ).order_by(Narrative.created_at.desc()).all()

    return [
        NarrativeResponse(
            id=n.id,
            version=n.version,
            status=n.status,
            script=n.script_text,
            scenes=[],  # Simplified for list view
            word_count=n.word_count,
            estimated_duration=n.estimated_duration_seconds,
            created_at=n.created_at,
        )
        for n in narratives
    ]


@router.get("/{narrative_id}", response_model=NarrativeResponse)
async def get_narrative(
    project_id: UUID,
    narrative_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Get full narrative with script."""
    narrative = db.query(Narrative).filter(
        Narrative.id == narrative_id,
        Narrative.project_id == project_id,
    ).first()

    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")

    # Parse scenes from JSON
    scenes = []
    if narrative.scenes:
        for i, scene_data in enumerate(narrative.scenes):
            scenes.append(NarrativeScene(
                id=str(i + 1),
                order=i + 1,
                text=scene_data.get("text", ""),
                content_ids=scene_data.get("content_ids", []),
                duration_seconds=scene_data.get("duration", 8),
                transition="fade",
            ))

    return NarrativeResponse(
        id=narrative.id,
        version=narrative.version,
        status=narrative.status,
        script=narrative.script_text,
        scenes=scenes,
        word_count=narrative.word_count,
        estimated_duration=narrative.estimated_duration_seconds,
        created_at=narrative.created_at,
    )


@router.post("/regenerate", response_model=NarrativeResponse)
async def regenerate_narrative(
    project_id: UUID,
    request: NarrativeRegenerateRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Regenerate the narrative with different parameters."""
    # Get project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None),
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get included content items
    content_query = db.query(ContentItem).filter(
        ContentItem.project_id == project_id,
        ContentItem.deleted_at.is_(None),
        ContentItem.included_in_narrative == True,
    )

    # Apply focus/exclude filters if provided
    if request and request.focus_content_ids:
        content_query = content_query.filter(ContentItem.id.in_(request.focus_content_ids))
    if request and request.exclude_content_ids:
        content_query = content_query.filter(~ContentItem.id.in_(request.exclude_content_ids))

    content_items = content_query.order_by(
        ContentItem.taken_at.asc().nullslast(),
        ContentItem.created_at.asc()
    ).all()

    if not content_items:
        raise HTTPException(
            status_code=400,
            detail="No content items selected for narrative generation"
        )

    # Check if API key is configured
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Narrative generation is not configured. Please set ANTHROPIC_API_KEY."
        )

    # Get current version number
    latest_narrative = db.query(Narrative).filter(
        Narrative.project_id == project_id,
    ).order_by(Narrative.version.desc()).first()

    new_version = (latest_narrative.version + 1) if latest_narrative else 1

    # Generate narrative with Claude
    try:
        tone = request.tone if request else None
        result = generate_narrative_with_claude(
            project_title=project.title,
            content_items=content_items,
            tone=tone,
        )
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to generate narrative: {str(e)}"
        )

    # Map content indices to actual content IDs for scenes
    content_id_map = {i + 1: str(item.id) for i, item in enumerate(content_items)}
    scenes_with_ids = []
    for scene in result["scenes"]:
        scene_content_ids = [
            content_id_map[idx]
            for idx in scene.get("content_indices", [])
            if idx in content_id_map
        ]
        scenes_with_ids.append({
            "text": scene["text"],
            "content_ids": scene_content_ids,
            "duration": scene["duration"],
        })

    # Create narrative record
    narrative = Narrative(
        project_id=project_id,
        version=new_version,
        status=NarrativeStatus.REVIEW,
        script_text=result["script_text"],
        scenes=scenes_with_ids,
        word_count=result["word_count"],
        estimated_duration_seconds=result["estimated_duration"],
        generation_params={"tone": tone} if tone else None,
        model_version="claude-sonnet-4-20250514",
    )

    db.add(narrative)

    # Update project's current narrative
    project.current_narrative_id = narrative.id

    db.commit()
    db.refresh(narrative)

    # Build response
    scenes_response = []
    for i, scene_data in enumerate(scenes_with_ids):
        scenes_response.append(NarrativeScene(
            id=str(i + 1),
            order=i + 1,
            text=scene_data.get("text", ""),
            content_ids=[UUID(cid) for cid in scene_data.get("content_ids", [])],
            duration_seconds=scene_data.get("duration", 8),
            transition="fade",
        ))

    return NarrativeResponse(
        id=narrative.id,
        version=narrative.version,
        status=narrative.status,
        script=narrative.script_text,
        scenes=scenes_response,
        word_count=narrative.word_count,
        estimated_duration=narrative.estimated_duration_seconds,
        created_at=narrative.created_at,
    )


@router.patch("/{narrative_id}/approve", response_model=NarrativeResponse)
async def approve_narrative(
    project_id: UUID,
    narrative_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Approve a narrative for video generation."""
    narrative = db.query(Narrative).filter(
        Narrative.id == narrative_id,
        Narrative.project_id == project_id,
    ).first()

    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found")

    narrative.status = NarrativeStatus.APPROVED
    db.commit()
    db.refresh(narrative)

    return NarrativeResponse(
        id=narrative.id,
        version=narrative.version,
        status=narrative.status,
        script=narrative.script_text,
        scenes=[],
        word_count=narrative.word_count,
        estimated_duration=narrative.estimated_duration_seconds,
        created_at=narrative.created_at,
    )

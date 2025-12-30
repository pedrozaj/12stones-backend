"""Content management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content import ContentItem
from app.models.user import User
from app.routers.auth import get_current_user_from_token
from app.schemas.content import ContentItemResponse, ContentUpdate, ImportRequest
from app.utils.storage import get_file_url

router = APIRouter()


@router.get("", response_model=list[ContentItemResponse])
async def list_content(
    project_id: UUID,
    type: str | None = None,
    source: str | None = None,
    analyzed: bool | None = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """List content items in a project."""
    query = db.query(ContentItem).filter(
        ContentItem.project_id == project_id,
        ContentItem.deleted_at.is_(None),
    )

    if type:
        query = query.filter(ContentItem.type == type)
    if source:
        query = query.filter(ContentItem.source == source)

    items = query.order_by(ContentItem.taken_at.desc().nullslast(), ContentItem.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    result = []
    for item in items:
        # Generate thumbnail URL if available
        thumbnail_url = None
        if item.thumbnail_r2_key:
            thumbnail_url = get_file_url(item.thumbnail_r2_key)
        elif item.r2_key and item.type.value == "photo":
            thumbnail_url = get_file_url(item.r2_key)

        result.append(ContentItemResponse(
            id=item.id,
            type=item.type,
            source=item.source,
            thumbnail_url=thumbnail_url,
            original_url=get_file_url(item.r2_key) if item.r2_key else None,
            caption=item.custom_caption or item.original_caption,
            taken_at=item.taken_at,
            location=item.location_name,
            analysis=None,  # TODO: Include analysis if available
            included_in_narrative=item.included_in_narrative,
            created_at=item.created_at,
        ))

    return result


@router.post("/upload")
async def upload_content(
    project_id: UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload content to a project."""
    # TODO: Implement file upload
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/import")
async def import_content(
    project_id: UUID,
    request: ImportRequest,
    db: Session = Depends(get_db),
):
    """Import content from connected social accounts."""
    # TODO: Implement social import
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{content_id}", response_model=ContentItemResponse)
async def get_content_item(
    project_id: UUID,
    content_id: UUID,
    db: Session = Depends(get_db),
):
    """Get content item details."""
    # TODO: Implement get content
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/{content_id}", response_model=ContentItemResponse)
async def update_content_item(
    project_id: UUID,
    content_id: UUID,
    request: ContentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Update content metadata or inclusion status."""
    # Get the content item
    item = db.query(ContentItem).filter(
        ContentItem.id == content_id,
        ContentItem.project_id == project_id,
        ContentItem.deleted_at.is_(None),
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")

    # Update fields if provided
    if request.included_in_narrative is not None:
        item.included_in_narrative = request.included_in_narrative
    if request.custom_caption is not None:
        item.custom_caption = request.custom_caption

    db.commit()
    db.refresh(item)

    # Generate URLs
    thumbnail_url = None
    if item.thumbnail_r2_key:
        thumbnail_url = get_file_url(item.thumbnail_r2_key)
    elif item.r2_key and item.type.value == "photo":
        thumbnail_url = get_file_url(item.r2_key)

    return ContentItemResponse(
        id=item.id,
        type=item.type,
        source=item.source,
        thumbnail_url=thumbnail_url,
        original_url=get_file_url(item.r2_key) if item.r2_key else None,
        caption=item.custom_caption or item.original_caption,
        taken_at=item.taken_at,
        location=item.location_name,
        analysis=None,
        included_in_narrative=item.included_in_narrative,
        created_at=item.created_at,
    )


@router.delete("/{content_id}")
async def delete_content_item(
    project_id: UUID,
    content_id: UUID,
    db: Session = Depends(get_db),
):
    """Remove content from project."""
    # TODO: Implement delete content
    return {"data": {"success": True}}

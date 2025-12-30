"""Instagram data export import endpoints."""

import json
import zipfile
from datetime import datetime
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content import ContentItem, ContentSource, ContentStatus, ContentType
from app.models.user import User
from app.routers.auth import get_current_user_from_token
from app.utils.storage import generate_upload_url, get_file_from_r2, upload_file_to_r2

router = APIRouter()


def get_content_type_from_filename(filename: str) -> ContentType:
    """Determine content type from filename."""
    lower = filename.lower()
    if lower.endswith((".mp4", ".mov", ".avi", ".webm")):
        return ContentType.VIDEO
    return ContentType.PHOTO


def get_mime_type_from_filename(filename: str) -> str:
    """Get MIME type from filename."""
    lower = filename.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    elif lower.endswith(".png"):
        return "image/png"
    elif lower.endswith(".gif"):
        return "image/gif"
    elif lower.endswith(".webp"):
        return "image/webp"
    elif lower.endswith(".mp4"):
        return "video/mp4"
    elif lower.endswith(".mov"):
        return "video/quicktime"
    elif lower.endswith(".avi"):
        return "video/x-msvideo"
    elif lower.endswith(".webm"):
        return "video/webm"
    return "application/octet-stream"


def parse_instagram_timestamp(timestamp: int | str) -> datetime | None:
    """Parse Instagram timestamp to datetime."""
    try:
        if isinstance(timestamp, int):
            return datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return None


def find_posts_json(zip_file: zipfile.ZipFile) -> dict | None:
    """Find and parse the posts or stories JSON file from Instagram export."""
    # Instagram export can have different structures
    possible_paths = [
        "content/posts_1.json",
        "your_instagram_activity/content/posts_1.json",
        "posts_1.json",
        "media.json",
        # Stories paths
        "your_instagram_activity/media/stories.json",
        "media/stories.json",
        "stories.json",
    ]

    for path in possible_paths:
        try:
            with zip_file.open(path) as f:
                return json.load(f)
        except KeyError:
            continue

    # Try to find any posts or stories JSON file
    for name in zip_file.namelist():
        if ("posts" in name.lower() or "stories" in name.lower()) and name.endswith(".json"):
            try:
                with zip_file.open(name) as f:
                    return json.load(f)
            except (json.JSONDecodeError, KeyError):
                continue

    return None


def find_media_file(zip_file: zipfile.ZipFile, uri: str) -> bytes | None:
    """Find a media file in the ZIP by its URI."""
    # URI might be relative path like "media/posts/202401/image.jpg"
    # or just the filename

    # Try exact path first
    try:
        with zip_file.open(uri) as f:
            return f.read()
    except KeyError:
        pass

    # Try finding by filename
    filename = uri.split("/")[-1]
    for name in zip_file.namelist():
        if name.endswith(filename):
            try:
                with zip_file.open(name) as f:
                    return f.read()
            except KeyError:
                continue

    return None


@router.post("/upload")
async def upload_instagram_export(
    project_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """
    Upload and process an Instagram data export ZIP file.

    The ZIP file should be the one downloaded from Instagram's
    "Download Your Information" feature (in JSON format).
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a ZIP archive",
        )

    # Read the ZIP file
    try:
        contents = await file.read()
        zip_buffer = BytesIO(contents)
        zip_file = zipfile.ZipFile(zip_buffer, "r")
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ZIP file",
        )

    # Find and parse posts JSON
    posts_data = find_posts_json(zip_file)
    if not posts_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find posts data in ZIP. Make sure you exported your data in JSON format from Instagram.",
        )

    imported_items = []
    errors = []

    # Process each post
    # Instagram export structure can vary, handle different formats
    posts = posts_data if isinstance(posts_data, list) else posts_data.get("ig_posts", posts_data.get("ig_stories", posts_data.get("posts", [])))

    for post in posts:
        try:
            # Get media items from post
            media_items = post.get("media", [])
            if not media_items:
                # Single media post (older format)
                media_items = [post]

            for media in media_items:
                # Get the media URI
                uri = media.get("uri", "")
                if not uri:
                    continue

                # Find the media file in ZIP
                media_data = find_media_file(zip_file, uri)
                if not media_data:
                    errors.append(f"Could not find media file: {uri}")
                    continue

                # Determine content type and MIME type
                filename = uri.split("/")[-1]
                content_type = get_content_type_from_filename(filename)
                mime_type = get_mime_type_from_filename(filename)

                # Upload to R2
                folder = f"users/{current_user.id}/projects/{project_id}/instagram"
                r2_key = upload_file_to_r2(
                    file_data=media_data,
                    filename=filename,
                    content_type=mime_type,
                    folder=folder,
                )

                # Parse metadata
                caption = media.get("title", "") or post.get("title", "")
                timestamp = media.get("creation_timestamp") or post.get("creation_timestamp")
                taken_at = parse_instagram_timestamp(timestamp)

                # Create content item
                content_item = ContentItem(
                    project_id=project_id,
                    type=content_type,
                    source=ContentSource.INSTAGRAM,
                    status=ContentStatus.READY,
                    r2_key=r2_key,
                    file_size_bytes=len(media_data),
                    mime_type=mime_type,
                    original_caption=caption,
                    source_id=uri,  # Use URI as source ID
                    taken_at=taken_at,
                )

                db.add(content_item)
                imported_items.append({
                    "filename": filename,
                    "type": content_type.value,
                    "caption": caption[:100] if caption else None,
                })

        except Exception as e:
            errors.append(f"Error processing post: {str(e)}")
            continue

    # Commit all items
    db.commit()

    zip_file.close()

    return {
        "success": True,
        "imported_count": len(imported_items),
        "imported_items": imported_items[:20],  # Return first 20 for preview
        "errors": errors[:10] if errors else [],  # Return first 10 errors
        "message": f"Successfully imported {len(imported_items)} items from Instagram export",
    }


@router.get("/upload-url")
async def get_upload_url(
    filename: str,
    current_user: User = Depends(get_current_user_from_token),
):
    """
    Get a presigned URL for direct upload to R2.

    This allows the frontend to upload large files directly to R2
    without going through the backend, which is much faster and
    more reliable for large files.
    """
    # Generate presigned URL for ZIP upload
    result = generate_upload_url(
        filename=filename,
        content_type="application/zip",
        folder=f"instagram-imports/{current_user.id}",
    )

    return {
        "upload_url": result["upload_url"],
        "key": result["key"],
    }


@router.post("/process")
async def process_uploaded_export(
    project_id: UUID,
    r2_key: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """
    Process an Instagram export ZIP that was already uploaded to R2.

    This is the second step after uploading directly to R2 using
    the presigned URL from /upload-url.
    """
    # Download the ZIP from R2
    try:
        contents = get_file_from_r2(r2_key)
        zip_buffer = BytesIO(contents)
        zip_file = zipfile.ZipFile(zip_buffer, "r")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read ZIP file from storage: {str(e)}",
        )

    # Find and parse posts JSON
    posts_data = find_posts_json(zip_file)
    if not posts_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find posts data in ZIP. Make sure you exported your data in JSON format from Instagram.",
        )

    imported_items = []
    errors = []

    # Process each post
    posts = posts_data if isinstance(posts_data, list) else posts_data.get("ig_posts", posts_data.get("ig_stories", posts_data.get("posts", [])))

    for post in posts:
        try:
            media_items = post.get("media", [])
            if not media_items:
                media_items = [post]

            for media in media_items:
                uri = media.get("uri", "")
                if not uri:
                    continue

                media_data = find_media_file(zip_file, uri)
                if not media_data:
                    errors.append(f"Could not find media file: {uri}")
                    continue

                filename = uri.split("/")[-1]
                content_type = get_content_type_from_filename(filename)
                mime_type = get_mime_type_from_filename(filename)

                folder = f"users/{current_user.id}/projects/{project_id}/instagram"
                r2_media_key = upload_file_to_r2(
                    file_data=media_data,
                    filename=filename,
                    content_type=mime_type,
                    folder=folder,
                )

                caption = media.get("title", "") or post.get("title", "")
                timestamp = media.get("creation_timestamp") or post.get("creation_timestamp")
                taken_at = parse_instagram_timestamp(timestamp)

                content_item = ContentItem(
                    project_id=project_id,
                    type=content_type,
                    source=ContentSource.INSTAGRAM,
                    status=ContentStatus.READY,
                    r2_key=r2_media_key,
                    file_size_bytes=len(media_data),
                    mime_type=mime_type,
                    original_caption=caption,
                    source_id=uri,
                    taken_at=taken_at,
                )

                db.add(content_item)
                imported_items.append({
                    "filename": filename,
                    "type": content_type.value,
                    "caption": caption[:100] if caption else None,
                })

        except Exception as e:
            errors.append(f"Error processing post: {str(e)}")
            continue

    db.commit()
    zip_file.close()

    return {
        "success": True,
        "imported_count": len(imported_items),
        "imported_items": imported_items[:20],
        "errors": errors[:10] if errors else [],
        "message": f"Successfully imported {len(imported_items)} items from Instagram export",
    }


@router.get("/instructions")
async def get_import_instructions():
    """Get instructions for exporting data from Instagram."""
    return {
        "title": "How to Export Your Instagram Data",
        "steps": [
            "Open the Instagram app on your phone",
            "Tap your profile picture in the lower right corner",
            "Tap the three bars icon (menu) in the upper right corner",
            "Select 'Accounts Center' or 'Your activity'",
            "Tap 'Download your information'",
            "Select 'Some of your information'",
            "Choose 'Posts' (and optionally 'Stories')",
            "IMPORTANT: Select 'JSON' as the format (not HTML)",
            "Select the date range you want to export",
            "Tap 'Create files' and wait for the download link",
            "Download the ZIP file and upload it here",
        ],
        "notes": [
            "The export process may take a few hours to a few days depending on how much data you have",
            "You'll receive a notification when your download is ready",
            "Make sure to select JSON format, not HTML",
            "The ZIP file contains your photos, videos, and their metadata",
        ],
    }

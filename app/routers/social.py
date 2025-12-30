"""Social media connection endpoints."""

from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.social import SocialConnection
from app.routers.auth import get_current_user_from_token
from app.models.user import User
from app.schemas.social import SocialConnectionResponse

router = APIRouter()
settings = get_settings()

# OAuth URLs for each platform
OAUTH_URLS = {
    "instagram": {
        "auth": "https://api.instagram.com/oauth/authorize",
        "token": "https://api.instagram.com/oauth/access_token",
        "scope": "user_profile,user_media",
    },
    "facebook": {
        "auth": "https://www.facebook.com/v18.0/dialog/oauth",
        "token": "https://graph.facebook.com/v18.0/oauth/access_token",
        "scope": "public_profile,email,user_photos",
    },
    "tiktok": {
        "auth": "https://www.tiktok.com/v2/auth/authorize/",
        "token": "https://open.tiktokapis.com/v2/oauth/token/",
        "scope": "user.info.basic,video.list",
    },
}


def get_oauth_credentials(platform: str) -> tuple[str, str]:
    """Get OAuth credentials for a platform."""
    if platform == "instagram":
        return settings.instagram_client_id, settings.instagram_client_secret
    elif platform == "facebook":
        return settings.facebook_app_id, settings.facebook_app_secret
    elif platform == "tiktok":
        return settings.tiktok_client_key, settings.tiktok_client_secret
    else:
        raise ValueError(f"Unknown platform: {platform}")


@router.get("/connections", response_model=list[SocialConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """List user's connected social accounts."""
    connections = db.execute(
        select(SocialConnection).where(
            SocialConnection.user_id == current_user.id,
            SocialConnection.deleted_at.is_(None),
        )
    ).scalars().all()

    return [SocialConnectionResponse.model_validate(c) for c in connections]


@router.get("/connect/{platform}")
async def connect_platform(
    platform: str,
    current_user: User = Depends(get_current_user_from_token),
):
    """Initiate OAuth flow for a platform."""
    valid_platforms = ["instagram", "facebook", "tiktok"]
    if platform not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")

    # Check if OAuth credentials are configured
    client_id, client_secret = get_oauth_credentials(platform)
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{platform.title()} OAuth is not configured. Please add {platform.upper()}_CLIENT_ID and {platform.upper()}_CLIENT_SECRET to environment variables.",
        )

    oauth_config = OAUTH_URLS[platform]
    redirect_uri = f"{settings.backend_url}/api/social/callback/{platform}"

    # Build OAuth URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": oauth_config["scope"],
        "response_type": "code",
        "state": str(current_user.id),  # Pass user ID in state
    }

    auth_url = f"{oauth_config['auth']}?{urlencode(params)}"
    return {"auth_url": auth_url}


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str,
    state: str | None = None,
    db: Session = Depends(get_db),
):
    """Handle OAuth callback from platform."""
    import httpx

    valid_platforms = ["instagram", "facebook", "tiktok"]
    if platform not in valid_platforms:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")

    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")

    user_id = UUID(state)
    client_id, client_secret = get_oauth_credentials(platform)
    oauth_config = OAUTH_URLS[platform]
    redirect_uri = f"{settings.backend_url}/api/social/callback/{platform}"

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        if platform == "facebook":
            # Facebook uses GET request with query params for token exchange
            token_params = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            }
            response = await client.get(oauth_config["token"], params=token_params)
        else:
            token_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
            response = await client.post(oauth_config["token"], data=token_data)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for token: {response.text}",
            )

        token_response = response.json()
        access_token = token_response.get("access_token")
        platform_user_id = None
        platform_username = None

        # Fetch user profile for Facebook
        if platform == "facebook" and access_token:
            profile_response = await client.get(
                "https://graph.facebook.com/v18.0/me",
                params={
                    "access_token": access_token,
                    "fields": "id,name,email",
                },
            )
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                platform_user_id = profile_data.get("id")
                platform_username = profile_data.get("name")
        else:
            platform_user_id = token_response.get("user_id") or token_response.get("open_id")

    # Save connection to database
    connection = SocialConnection(
        user_id=user_id,
        platform=platform,
        platform_user_id=str(platform_user_id) if platform_user_id else None,
        username=platform_username,
        access_token=access_token,
        refresh_token=token_response.get("refresh_token"),
    )

    db.add(connection)
    db.commit()

    # Redirect back to frontend
    return RedirectResponse(url=f"{settings.frontend_url}/connections?connected={platform}")


@router.delete("/connections/{connection_id}")
async def disconnect_platform(
    connection_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Disconnect a social account."""
    from datetime import datetime

    connection = db.execute(
        select(SocialConnection).where(
            SocialConnection.id == connection_id,
            SocialConnection.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    connection.deleted_at = datetime.utcnow()
    db.commit()

    return {"success": True}


@router.post("/connections/{connection_id}/sync")
async def sync_connection(
    connection_id: UUID,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Trigger content sync from connected account."""
    connection = db.execute(
        select(SocialConnection).where(
            SocialConnection.id == connection_id,
            SocialConnection.user_id == current_user.id,
            SocialConnection.deleted_at.is_(None),
        )
    ).scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # TODO: Trigger async sync job via Celery
    # This would fetch content from the platform and save to our storage

    return {"success": True, "message": "Sync started"}

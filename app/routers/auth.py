"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    # TODO: Implement registration
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return tokens."""
    # TODO: Implement login
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/logout")
async def logout():
    """Log out user and invalidate tokens."""
    # TODO: Implement logout
    return {"data": {"success": True}}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token():
    """Refresh access token."""
    # TODO: Implement token refresh
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """Get current authenticated user."""
    # TODO: Implement get current user
    raise HTTPException(status_code=501, detail="Not implemented")

"""Authentication endpoints."""
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict

from ..models.schemas import UserCreate, UserLogin, UserResponse, Token
from ..core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)


router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate) -> Dict:
    """Register a new user."""
    # In production: Check if user exists, hash password, save to DB
    return {
        "id": 1,
        "email": user_data.email,
        "username": user_data.username,
        "created_at": "2024-01-01T00:00:00",
        "is_active": True,
        "is_premium": False,
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin) -> Dict:
    """Login and get access token."""
    # In production: Verify credentials, check DB
    # For demo, accept any credentials
    access_token = create_access_token(
        data={"sub": credentials.email, "user_id": 1}
    )
    refresh_token = create_refresh_token(
        data={"sub": credentials.email, "user_id": 1}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str) -> Dict:
    """Refresh access token."""
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    new_access_token = create_access_token(
        data={"sub": payload["sub"], "user_id": payload["user_id"]}
    )

    return {"access_token": new_access_token}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)) -> Dict:
    """Get current user info."""
    return {
        "id": current_user.get("user_id", 1),
        "email": current_user.get("sub", "user@example.com"),
        "username": "demo_user",
        "created_at": "2024-01-01T00:00:00",
        "is_active": True,
        "is_premium": False,
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> Dict:
    """Logout (invalidate token - implement token blacklist in production)."""
    return {"message": "Logged out successfully"}

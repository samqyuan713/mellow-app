"""
Mellow — Auth Router
All authentication endpoints: register, login, OAuth, password reset.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    RegisterRequest, LoginRequest, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest, GoogleAuthRequest,
    TokenResponse, AuthResponse
)
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new account with email and password."""
    return await AuthService.register(data, db)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    return await AuthService.login(data, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    return await AuthService.refresh_tokens(data.refresh_token, db)


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Verify email address using the token sent to the user."""
    return await AuthService.verify_email(data.token, db)


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password reset email."""
    return await AuthService.forgot_password(data.email, db)


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using the token from the reset email."""
    return await AuthService.reset_password(data.token, data.new_password, db)


@router.post("/google", response_model=AuthResponse)
async def google_oauth(data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Login or register via Google OAuth2."""
    return await AuthService.google_oauth(data.code, db)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's basic info."""
    return {
        "id":                str(current_user.id),
        "email":             current_user.email,
        "is_email_verified": current_user.is_email_verified,
        "role":              current_user.role,
        "has_profile":       current_user.profile is not None,
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout endpoint.
    JWT is stateless — client should delete the token.
    In production, add token to a Redis blocklist here.
    """
    return {"message": "Logged out successfully"}

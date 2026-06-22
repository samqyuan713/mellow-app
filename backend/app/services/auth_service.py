"""
Mellow — Auth Service
Core authentication business logic.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
import httpx
import logging

from app.models.user import User
from app.models.subscription import Subscription
from app.schemas.auth import (
    RegisterRequest, LoginRequest,
    TokenResponse, AuthResponse, UserResponse
)
from app.utils.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, generate_secure_token
)
from app.config import settings

logger = logging.getLogger("mellow.auth")


def _build_tokens(user: User) -> TokenResponse:
    """Build access + refresh token pair for a user."""
    return TokenResponse(
        access_token=create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role
        ),
        refresh_token=create_refresh_token(user_id=user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _build_user_response(user: User) -> UserResponse:
    """Build the user response object."""
    plan = "free"
    if user.subscription:
        plan = user.subscription.plan
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_email_verified=user.is_email_verified,
        role=user.role,
        created_at=user.created_at,
        has_profile=user.profile is not None,
        subscription_plan=plan,
    )


class AuthService:

    # ── Register ───────────────────────────────────────────────
    @staticmethod
    async def register(data: RegisterRequest, db: AsyncSession) -> AuthResponse:
        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == data.email.lower())
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists"
            )

        # Create user
        verify_token = generate_secure_token(32)
        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            email_verify_token=verify_token,
        )
        db.add(user)
        await db.flush()   # get user.id before commit

        # Auto-create free subscription
        subscription = Subscription(user_id=user.id, plan="free")
        db.add(subscription)
        await db.commit()
        await db.refresh(user)

        logger.info(f"New user registered: {user.email}")

        # TODO: Send verification email via email_service
        # await EmailService.send_verification_email(user.email, verify_token)

        tokens = _build_tokens(user)
        return AuthResponse(
            user=_build_user_response(user),
            tokens=tokens,
            message="Account created! Please verify your email."
        )

    # ── Login ──────────────────────────────────────────────────
    @staticmethod
    async def login(data: LoginRequest, db: AsyncSession) -> AuthResponse:
        result = await db.execute(
            select(User).where(
                User.email == data.email.lower(),
                User.deleted_at.is_(None)
            )
        )
        user = result.scalar_one_or_none()

        # Generic error — don't reveal whether email exists
        invalid_credentials = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

        if not user or not user.password_hash:
            raise invalid_credentials
        if not verify_password(data.password, user.password_hash):
            raise invalid_credentials
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        if user.is_banned:
            raise HTTPException(status_code=403, detail="Account has been suspended")

        # Update last login
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(last_login=datetime.now(timezone.utc))
        )
        await db.commit()
        await db.refresh(user)

        logger.info(f"User logged in: {user.email}")
        return AuthResponse(
            user=_build_user_response(user),
            tokens=_build_tokens(user),
            message="Welcome back!"
        )

    # ── Refresh Token ──────────────────────────────────────────
    @staticmethod
    async def refresh_tokens(refresh_token: str, db: AsyncSession) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = UUID(payload["sub"])

        result = await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        return _build_tokens(user)

    # ── Verify Email ───────────────────────────────────────────
    @staticmethod
    async def verify_email(token: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(User).where(User.email_verify_token == token)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid verification token")
        if user.is_email_verified:
            return {"message": "Email already verified"}

        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(is_email_verified=True, email_verify_token=None)
        )
        await db.commit()
        logger.info(f"Email verified: {user.email}")
        return {"message": "Email verified successfully!"}

    # ── Forgot Password ────────────────────────────────────────
    @staticmethod
    async def forgot_password(email: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()

        # Always return success (don't reveal if email exists)
        if user and user.is_active:
            reset_token = generate_secure_token(32)
            expiry = datetime.now(timezone.utc).replace(
                tzinfo=None
            ).replace(hour=datetime.now().hour + 1)

            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(reset_token=reset_token, reset_token_expiry=expiry)
            )
            await db.commit()
            # TODO: await EmailService.send_reset_email(user.email, reset_token)
            logger.info(f"Password reset requested: {user.email}")

        return {"message": "If that email exists, a reset link has been sent."}

    # ── Reset Password ─────────────────────────────────────────
    @staticmethod
    async def reset_password(token: str, new_password: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(User).where(
                User.reset_token == token,
                User.reset_token_expiry >= datetime.utcnow()
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                password_hash=hash_password(new_password),
                reset_token=None,
                reset_token_expiry=None
            )
        )
        await db.commit()
        logger.info(f"Password reset completed: {user.email}")
        return {"message": "Password updated successfully. Please log in."}

    # ── Google OAuth ───────────────────────────────────────────
    @staticmethod
    async def google_oauth(code: str, db: AsyncSession) -> AuthResponse:
        """Exchange Google auth code for user info and login/register."""
        try:
            async with httpx.AsyncClient() as client:
                # Exchange code for tokens
                token_resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code":          code,
                        "client_id":     settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
                        "grant_type":    "authorization_code",
                    }
                )
                token_data = token_resp.json()
                if "error" in token_data:
                    raise HTTPException(status_code=400, detail="Google OAuth failed")

                # Get user info
                user_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                google_user = user_resp.json()

        except Exception as e:
            logger.error(f"Google OAuth error: {e}")
            raise HTTPException(status_code=400, detail="Google authentication failed")

        google_id = google_user.get("id")
        email     = google_user.get("email", "").lower()

        if not email:
            raise HTTPException(status_code=400, detail="Could not get email from Google")

        # Find existing user by google_id or email
        result = await db.execute(
            select(User).where(
                (User.google_id == google_id) | (User.email == email)
            )
        )
        user = result.scalar_one_or_none()

        if user:
            # Update google_id if missing
            if not user.google_id:
                await db.execute(
                    update(User).where(User.id == user.id)
                    .values(google_id=google_id, is_email_verified=True)
                )
                await db.commit()
                await db.refresh(user)
            message = "Welcome back!"
        else:
            # Register new user via Google
            user = User(
                email=email,
                google_id=google_id,
                is_email_verified=True,   # Google emails are pre-verified
            )
            db.add(user)
            await db.flush()
            sub = Subscription(user_id=user.id, plan="free")
            db.add(sub)
            await db.commit()
            await db.refresh(user)
            message = "Account created via Google!"
            logger.info(f"New Google user: {email}")

        return AuthResponse(
            user=_build_user_response(user),
            tokens=_build_tokens(user),
            message=message
        )

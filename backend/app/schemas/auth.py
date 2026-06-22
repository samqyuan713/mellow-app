"""
Mellow — Auth Schemas
Pydantic models for request validation and response serialization.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re


# ── Register ───────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email:      EmailStr
    password:   str
    first_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("first_name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 50:
            raise ValueError("Name must be under 50 characters")
        return v


# ── Login ──────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


# ── Tokens ─────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int           # seconds until access token expires


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Password Reset ─────────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


# ── Email Verify ───────────────────────────────────────────────
class VerifyEmailRequest(BaseModel):
    token: str


# ── Google OAuth ───────────────────────────────────────────────
class GoogleAuthRequest(BaseModel):
    code:         str
    redirect_uri: Optional[str] = None


# ── User Response ──────────────────────────────────────────────
class UserResponse(BaseModel):
    id:                 str
    email:              str
    is_email_verified:  bool
    role:               str
    created_at:         datetime
    has_profile:        bool
    subscription_plan:  str = "free"

    model_config = {"from_attributes": True}


# ── Auth Response (login/register) ─────────────────────────────
class AuthResponse(BaseModel):
    user:   UserResponse
    tokens: TokenResponse
    message: str = "Success"

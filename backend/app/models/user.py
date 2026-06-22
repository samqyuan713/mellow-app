"""
Mellow — User Model
Core authentication table.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    # ── Identity ───────────────────────────────────────────────
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    phone        = Column(String(20), unique=True, nullable=True)

    # ── Auth ───────────────────────────────────────────────────
    password_hash = Column(String(255), nullable=True)   # NULL for OAuth-only users
    google_id     = Column(String(255), unique=True, nullable=True)

    # ── Verification ───────────────────────────────────────────
    is_email_verified  = Column(Boolean, default=False)
    is_phone_verified  = Column(Boolean, default=False)
    email_verify_token = Column(String(255), nullable=True)
    reset_token        = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    # ── Status ─────────────────────────────────────────────────
    is_active  = Column(Boolean, default=True)
    is_banned  = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    role       = Column(String(20), default="user")  # user / admin / moderator

    # ── Timestamps ─────────────────────────────────────────────
    created_at  = Column(DateTime, default=datetime.utcnow)
    last_login  = Column(DateTime, nullable=True)
    deleted_at  = Column(DateTime, nullable=True)   # soft delete

    # ── Relationships ──────────────────────────────────────────
    profile      = relationship("Profile",      back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def display_name(self) -> str:
        if self.profile:
            return self.profile.first_name
        return self.email.split("@")[0]

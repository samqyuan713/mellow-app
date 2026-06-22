"""
Mellow — Profile Model
Dating profile linked to a user account.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    Text, Float, ARRAY, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    # ── Identity ───────────────────────────────────────────────
    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # ── Basic Info ─────────────────────────────────────────────
    first_name = Column(String(50),  nullable=False)
    age        = Column(Integer,     nullable=False)
    gender     = Column(String(20),  nullable=False)
    seeking    = Column(String(20),  nullable=False)   # men / women / everyone

    # ── Location ───────────────────────────────────────────────
    location_city    = Column(String(100), nullable=True)
    location_country = Column(String(100), nullable=True)
    latitude         = Column(Float,       nullable=True)
    longitude        = Column(Float,       nullable=True)

    # ── About ──────────────────────────────────────────────────
    bio        = Column(Text,        nullable=True)
    occupation = Column(String(100), nullable=True)
    education  = Column(String(100), nullable=True)
    height_cm  = Column(Integer,     nullable=True)

    # ── Life Stage (critical for Mellow niche) ────────────────
    marital_history   = Column(String(50), nullable=True)  # divorced/widowed/never-married/separated
    has_children      = Column(String(20), nullable=True)  # yes/no/sometimes
    wants_children    = Column(String(20), nullable=True)  # yes/no/open
    relationship_goal = Column(String(50), nullable=True)  # serious/casual/friendship/unsure

    # ── Lifestyle ──────────────────────────────────────────────
    religion  = Column(String(50), nullable=True)
    drinking  = Column(String(30), nullable=True)  # never/socially/regularly
    smoking   = Column(String(30), nullable=True)  # never/occasionally/regularly

    # ── Preferences (who they want to match with) ──────────────
    pref_age_min      = Column(Integer, default=35)
    pref_age_max      = Column(Integer, default=65)
    pref_distance_km  = Column(Integer, default=50)

    # ── Arrays ─────────────────────────────────────────────────
    interests = Column(ARRAY(String), default=[])
    languages = Column(ARRAY(String), default=[])

    # ── Status ─────────────────────────────────────────────────
    profile_complete = Column(Boolean, default=False)
    is_visible       = Column(Boolean, default=True)
    is_verified      = Column(Boolean, default=False)   # photo verified

    # ── Timestamps ─────────────────────────────────────────────
    last_active = Column(DateTime, default=datetime.utcnow)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Constraints ────────────────────────────────────────────
    __table_args__ = (
        CheckConstraint("age >= 30 AND age <= 80", name="check_age_range"),
        CheckConstraint("height_cm IS NULL OR (height_cm >= 100 AND height_cm <= 250)", name="check_height"),
    )

    # ── Relationships ──────────────────────────────────────────
    user   = relationship("User",  back_populates="profile")
    photos = relationship("Photo", back_populates="profile", cascade="all, delete-orphan", order_by="Photo.sort_order")

    def __repr__(self):
        return f"<Profile id={self.id} name={self.first_name} age={self.age}>"

    @property
    def primary_photo(self):
        """Return the primary photo or the first photo."""
        for photo in self.photos:
            if photo.is_primary:
                return photo
        return self.photos[0] if self.photos else None

    @property
    def completion_percentage(self) -> int:
        """Calculate how complete the profile is (0-100)."""
        fields = [
            self.first_name, self.age, self.gender, self.seeking,
            self.bio, self.occupation, self.location_city,
            self.marital_history, self.relationship_goal,
            self.interests,
        ]
        filled = sum(1 for f in fields if f)
        has_photos = 1 if self.photos else 0
        total = len(fields) + 1
        return round(((filled + has_photos) / total) * 100)


class Photo(Base):
    __tablename__ = "photos"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id    = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    cloudinary_id = Column(String(255), nullable=False)
    url           = Column(Text, nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    is_primary    = Column(Boolean, default=False)
    is_approved   = Column(Boolean, default=True)   # set False if moderation flags it
    sort_order    = Column(Integer, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # ── Relationships ──────────────────────────────────────────
    profile = relationship("Profile", back_populates="photos")

    def __repr__(self):
        return f"<Photo id={self.id} profile={self.profile_id}>"

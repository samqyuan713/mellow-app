"""
Mellow — Profile Schemas
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ── Photo ──────────────────────────────────────────────────────
class PhotoResponse(BaseModel):
    id:            UUID
    url:           str
    thumbnail_url: Optional[str]
    is_primary:    bool
    sort_order:    int

    model_config = {"from_attributes": True}


# ── Create / Update Profile ────────────────────────────────────
class ProfileCreateRequest(BaseModel):
    first_name:        str
    age:               int
    gender:            str
    seeking:           str
    bio:               Optional[str]   = None
    occupation:        Optional[str]   = None
    education:         Optional[str]   = None
    height_cm:         Optional[int]   = None
    location_city:     Optional[str]   = None
    location_country:  Optional[str]   = None
    marital_history:   Optional[str]   = None
    has_children:      Optional[str]   = None
    wants_children:    Optional[str]   = None
    relationship_goal: Optional[str]   = None
    religion:          Optional[str]   = None
    drinking:          Optional[str]   = None
    smoking:           Optional[str]   = None
    interests:         Optional[List[str]] = []
    languages:         Optional[List[str]] = []
    pref_age_min:      Optional[int]   = 35
    pref_age_max:      Optional[int]   = 65
    pref_distance_km:  Optional[int]   = 50

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v < 30 or v > 80:
            raise ValueError("Age must be between 30 and 80")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        allowed = ["man", "woman", "non-binary", "other"]
        if v.lower() not in allowed:
            raise ValueError(f"Gender must be one of: {allowed}")
        return v.lower()

    @field_validator("seeking")
    @classmethod
    def validate_seeking(cls, v):
        allowed = ["men", "women", "everyone"]
        if v.lower() not in allowed:
            raise ValueError(f"Seeking must be one of: {allowed}")
        return v.lower()

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v):
        if v and len(v) > 500:
            raise ValueError("Bio must be under 500 characters")
        return v

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, v):
        if v and len(v) > 10:
            raise ValueError("Maximum 10 interests allowed")
        return v


class ProfileUpdateRequest(ProfileCreateRequest):
    first_name: Optional[str] = None
    age:        Optional[int] = None
    gender:     Optional[str] = None
    seeking:    Optional[str] = None


# ── Profile Response ───────────────────────────────────────────
class ProfileResponse(BaseModel):
    id:                UUID
    first_name:        str
    age:               int
    gender:            str
    seeking:           str
    bio:               Optional[str]
    occupation:        Optional[str]
    education:         Optional[str]
    height_cm:         Optional[int]
    location_city:     Optional[str]
    location_country:  Optional[str]
    marital_history:   Optional[str]
    has_children:      Optional[str]
    wants_children:    Optional[str]
    relationship_goal: Optional[str]
    religion:          Optional[str]
    drinking:          Optional[str]
    smoking:           Optional[str]
    interests:         List[str]
    languages:         List[str]
    is_visible:        bool
    is_verified:       bool
    profile_complete:  bool
    completion_pct:    int
    photos:            List[PhotoResponse]
    last_active:       datetime
    created_at:        datetime

    model_config = {"from_attributes": True}


# ── Discovery Card (shown during swiping — limited info) ───────
class DiscoverCardResponse(BaseModel):
    id:                UUID
    first_name:        str
    age:               int
    occupation:        Optional[str]
    location_city:     Optional[str]
    bio:               Optional[str]
    marital_history:   Optional[str]
    relationship_goal: Optional[str]
    interests:         List[str]
    photos:            List[PhotoResponse]
    compatibility_score: Optional[int]   = None

    model_config = {"from_attributes": True}


# ── Photo Reorder ──────────────────────────────────────────────
class PhotoReorderRequest(BaseModel):
    photo_ids: List[UUID]   # ordered list — first becomes primary


# ── Visibility ─────────────────────────────────────────────────
class VisibilityUpdateRequest(BaseModel):
    is_visible: bool

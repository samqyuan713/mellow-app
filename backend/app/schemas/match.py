"""
Mellow — Match, Message & Subscription Schemas
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Union
from datetime import datetime
from uuid import UUID
from app.schemas.profile import PhotoResponse


# ══════════════════════════════════════════
# MATCH SCHEMAS
# ══════════════════════════════════════════

class SwipeRequest(BaseModel):
    profile_id: UUID
    direction:  str     # like / pass / superlike

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        allowed = ["like", "pass", "superlike"]
        if v not in allowed:
            raise ValueError(f"Direction must be one of: {allowed}")
        return v


class SwipeResponse(BaseModel):
    matched:    bool
    match_id:   Optional[UUID] = None
    message:    str


class MatchedProfileSnippet(BaseModel):
    id:           UUID
    first_name:   str
    age:          int
    primary_photo: Optional[PhotoResponse]

    model_config = {"from_attributes": True}


class MatchResponse(BaseModel):
    id:              UUID
    matched_at:      datetime
    is_active:       bool
    last_message_at: Optional[datetime]
    other_profile:   MatchedProfileSnippet
    unread_count:    int = 0

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════
# MESSAGE SCHEMAS
# ══════════════════════════════════════════

class SendMessageRequest(BaseModel):
    content:      str
    message_type: str = "text"

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 1000:
            raise ValueError("Message must be under 1000 characters")
        return v


class MessageResponse(BaseModel):
    id:           UUID
    match_id:     UUID
    sender_id:    UUID
    content:      str
    message_type: str
    is_read:      bool
    read_at:      Optional[datetime]
    created_at:   datetime
    is_mine:      bool = False     # set in service layer based on current user

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    match_id:       UUID
    other_profile:  MatchedProfileSnippet
    messages:       List[MessageResponse]
    total:          int

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════
# SUBSCRIPTION SCHEMAS
# ══════════════════════════════════════════

class PlanFeatures(BaseModel):
    daily_swipes:       Union[int, str]    # int or "unlimited"
    messages_per_match: Union[int, str]
    max_photos:         int
    advanced_filters:   bool
    read_receipts:      bool
    see_who_liked_you:  bool
    boosts_per_month:   int
    priority_discovery: bool


class PlanResponse(BaseModel):
    id:              str
    name:            str
    price_monthly:   float
    stripe_price_id: str
    features:        PlanFeatures


class SubscriptionResponse(BaseModel):
    plan:                 str
    status:               str
    is_premium:           bool
    is_plus:              bool
    current_period_end:   Optional[datetime]
    cancel_at_period_end: bool

    model_config = {"from_attributes": True}


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id:   str


class CustomerPortalResponse(BaseModel):
    portal_url: str


# ══════════════════════════════════════════
# SAFETY SCHEMAS
# ══════════════════════════════════════════

class ReportRequest(BaseModel):
    reported_user_id: UUID
    reason:           str
    description:      Optional[str] = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v):
        allowed = [
            "inappropriate_photos", "harassment", "fake_profile",
            "spam", "underage", "hate_speech", "scam", "other"
        ]
        if v not in allowed:
            raise ValueError(f"Reason must be one of: {allowed}")
        return v


class BlockRequest(BaseModel):
    blocked_user_id: UUID


class SafetyResponse(BaseModel):
    success: bool
    message: str

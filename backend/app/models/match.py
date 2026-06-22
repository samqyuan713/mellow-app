"""
Mellow — Match & Swipe Models
"""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date,
    Integer, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Swipe(Base):
    __tablename__ = "swipes"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    swiper_id  = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    swiped_id  = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    direction  = Column(String(10), nullable=False)   # like / pass / superlike
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("swiper_id", "swiped_id", name="uq_swipe"),
    )

    def __repr__(self):
        return f"<Swipe {self.swiper_id} → {self.direction} → {self.swiped_id}>"


class Match(Base):
    __tablename__ = "matches"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_1_id   = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_2_id   = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    matched_at     = Column(DateTime, default=datetime.utcnow)
    is_active      = Column(Boolean, default=True)
    last_message_at = Column(DateTime, nullable=True)

    # ── Relationships ──────────────────────────────────────────
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("profile_1_id", "profile_2_id", name="uq_match"),
    )

    def other_profile_id(self, my_profile_id) -> UUID:
        """Return the other person's profile ID in this match."""
        return self.profile_2_id if self.profile_1_id == my_profile_id else self.profile_1_id

    def __repr__(self):
        return f"<Match {self.profile_1_id} ↔ {self.profile_2_id}>"


class DailyLimit(Base):
    """Tracks free-tier usage per user per day."""
    __tablename__ = "daily_limits"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date            = Column(Date, default=date.today)
    swipes_used     = Column(Integer, default=0)
    messages_sent   = Column(Integer, default=0)
    superlikes_used = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_limit"),
    )

    def __repr__(self):
        return f"<DailyLimit user={self.user_id} date={self.date} swipes={self.swipes_used}>"

"""
Mellow — Subscription, Report & Block Models
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id              = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    stripe_customer_id   = Column(String(255), unique=True, nullable=True)
    stripe_sub_id        = Column(String(255), unique=True, nullable=True)
    plan                 = Column(String(20), default="free")    # free / mellow / mellow_plus
    status               = Column(String(20), default="active")  # active / cancelled / past_due
    current_period_start = Column(DateTime, nullable=True)
    current_period_end   = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ──────────────────────────────────────────
    user = relationship("User", back_populates="subscription")

    @property
    def is_premium(self) -> bool:
        return self.plan in ("mellow", "mellow_plus") and self.status == "active"

    @property
    def is_plus(self) -> bool:
        return self.plan == "mellow_plus" and self.status == "active"

    def __repr__(self):
        return f"<Subscription user={self.user_id} plan={self.plan} status={self.status}>"


class Report(Base):
    __tablename__ = "reports"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reported_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason      = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status      = Column(String(20), default="pending")   # pending / reviewed / resolved
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Report {self.reporter_id} → {self.reported_id} [{self.status}]>"


class Block(Base):
    __tablename__ = "blocks"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_block"),
    )

    def __repr__(self):
        return f"<Block {self.blocker_id} → {self.blocked_id}>"

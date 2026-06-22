"""
Mellow — Message Model
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id     = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id    = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    content      = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")    # text / image / emoji
    is_read      = Column(Boolean, default=False)
    read_at      = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    deleted_at   = Column(DateTime, nullable=True)       # soft delete

    # ── Relationships ──────────────────────────────────────────
    match = relationship("Match", back_populates="messages")

    def __repr__(self):
        return f"<Message id={self.id} match={self.match_id}>"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

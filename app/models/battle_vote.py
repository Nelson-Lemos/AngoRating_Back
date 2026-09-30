import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class BattleVote(Base):
    __tablename__ = "battle_votes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    company_a_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    company_b_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    voted_for = Column(String(36), ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")

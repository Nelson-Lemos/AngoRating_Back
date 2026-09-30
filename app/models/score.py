import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base


class CompanyScore(Base):
    __tablename__ = "company_scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), ForeignKey("companies.id"), unique=True, nullable=False, index=True)
    score = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    service_score = Column(Float, default=0.0)
    price_score = Column(Float, default=0.0)
    reliability_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    confidence_level = Column(String(20), default="LOW")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="score")

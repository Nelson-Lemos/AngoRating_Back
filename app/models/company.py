import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Float, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    logo = Column(String(500), nullable=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False, index=True)
    location_id = Column(String(36), ForeignKey("locations.id"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category = relationship("Category", back_populates="companies")
    location = relationship("Location", back_populates="companies")
    owner = relationship("User", backref="owned_companies")
    reviews = relationship("Review", back_populates="company")
    score = relationship("CompanyScore", back_populates="company", uselist=False)
    score_history = relationship("ScoreHistory", back_populates="company")

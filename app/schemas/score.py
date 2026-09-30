from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CompanyScoreResponse(BaseModel):
    company_id: str
    score: float
    quality_score: float
    service_score: float
    price_score: float
    reliability_score: float
    experience_score: float
    total_reviews: int
    confidence_level: str
    updated_at: datetime

    class Config:
        from_attributes = True


class ScoreHistoryResponse(BaseModel):
    id: str
    company_id: str
    score: float
    total_reviews: int
    created_at: datetime

    class Config:
        from_attributes = True


class RankingItem(BaseModel):
    company_id: str
    company_name: str
    slug: str
    category_name: Optional[str] = None
    location_name: Optional[str] = None
    score: float
    total_reviews: int
    confidence_level: str
    trend: Optional[float] = None

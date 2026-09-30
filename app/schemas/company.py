from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CompanyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo: Optional[str] = None
    category_id: str
    location_id: str


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo: Optional[str] = None
    category_id: Optional[str] = None
    location_id: Optional[str] = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    logo: Optional[str] = None
    category_id: str
    location_id: str
    owner_id: Optional[str] = None
    is_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyDetail(CompanyResponse):
    category_name: Optional[str] = None
    location_name: Optional[str] = None
    score: Optional[float] = None
    total_reviews: int = 0
    confidence_level: str = "LOW"

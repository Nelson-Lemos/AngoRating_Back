from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReviewCreate(BaseModel):
    company_id: str
    quality: int = Field(ge=1, le=5)
    service: int = Field(ge=1, le=5)
    price: int = Field(ge=1, le=5)
    reliability: int = Field(ge=1, le=5)
    experience: int = Field(ge=1, le=5)
    mode: Optional[str] = Field(default=None, pattern="^(new|update)$")


class ReviewResponse(BaseModel):
    id: str
    user_id: str
    company_id: str
    quality: int
    service: int
    price: int
    reliability: int
    experience: int
    is_valid: bool
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True

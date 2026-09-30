from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    review_id: str
    company_id: str
    reason: str
    description: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    user_id: str
    review_id: str
    company_id: str
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

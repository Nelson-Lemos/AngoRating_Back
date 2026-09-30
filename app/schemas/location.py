from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LocationResponse(BaseModel):
    id: str
    name: str
    type: str
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True


class LocationTree(LocationResponse):
    children: List["LocationTree"] = []

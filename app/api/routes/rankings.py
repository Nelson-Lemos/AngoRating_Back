from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.services import ranking_service

router = APIRouter(prefix="/api/v1/rankings", tags=["Rankings"])


@router.get("/top")
def top_ranking(
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = ranking_service.get_top_ranking(db, category_id, location_id, limit)
    return {"items": [i.model_dump() for i in items]}


@router.get("/trending")
def trending_ranking(
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = ranking_service.get_trending_ranking(db, category_id, location_id, limit)
    return {"items": [i.model_dump() for i in items]}


@router.get("/most-rated")
def most_rated_ranking(
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = ranking_service.get_most_rated_ranking(db, category_id, location_id, limit)
    return {"items": [i.model_dump() for i in items]}


@router.get("/rising")
def rising_ranking(
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = ranking_service.get_rising_ranking(db, category_id, location_id, limit)
    return {"items": [i.model_dump() for i in items]}


@router.get("/declining")
def declining_ranking(
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = ranking_service.get_declining_ranking(db, category_id, location_id, limit)
    return {"items": [i.model_dump() for i in items]}

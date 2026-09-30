from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional

from app.models.company import Company
from app.models.score import CompanyScore
from app.models.ranking import ScoreHistory
from app.schemas.score import RankingItem


def _build_ranking_item(company: Company, score: CompanyScore, trend: float = 0.0) -> RankingItem:
    return RankingItem(
        company_id=company.id,
        company_name=company.name,
        slug=company.slug,
        category_name=company.category.name if company.category else None,
        location_name=company.location.name if company.location else None,
        score=score.score if score else 0.0,
        total_reviews=score.total_reviews if score else 0,
        confidence_level=score.confidence_level if score else "LOW",
        trend=trend,
    )


def _calc_trend(db: Session, company_id: str) -> float:
    recent = (
        db.query(ScoreHistory)
        .filter(ScoreHistory.company_id == company_id)
        .order_by(ScoreHistory.created_at.desc())
        .limit(2)
        .all()
    )
    if len(recent) < 2:
        return 0.0
    return round(recent[0].score - recent[1].score, 1)


def get_top_ranking(
    db: Session,
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = 20,
):
    query = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews > 0)
    )
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)
    results = query.order_by(desc(CompanyScore.score)).limit(limit).all()
    return [_build_ranking_item(c, s, _calc_trend(db, c.id)) for c, s in results]


def get_trending_ranking(
    db: Session,
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = 20,
):
    query = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews >= 5)
    )
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)
    results = query.all()

    items = []
    for c, s in results:
        trend = _calc_trend(db, c.id)
        if trend > 0:
            items.append((_build_ranking_item(c, s, trend), trend))
    items.sort(key=lambda x: -x[1])
    return [item for item, _ in items[:limit]]


def get_most_rated_ranking(
    db: Session,
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = 20,
):
    query = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews > 0)
    )
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)
    results = query.order_by(desc(CompanyScore.total_reviews)).limit(limit).all()
    return [_build_ranking_item(c, s, _calc_trend(db, c.id)) for c, s in results]


def get_rising_ranking(
    db: Session,
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = 20,
):
    query = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews >= 3)
    )
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)
    results = query.all()

    items = []
    for c, s in results:
        trend = _calc_trend(db, c.id)
        if trend > 0:
            items.append((_build_ranking_item(c, s, trend), trend))
    items.sort(key=lambda x: -x[1])
    return [item for item, _ in items[:limit]]


def get_declining_ranking(
    db: Session,
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = 20,
):
    query = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews >= 5)
    )
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)
    results = query.all()

    items = []
    for c, s in results:
        trend = _calc_trend(db, c.id)
        if trend < 0:
            items.append((_build_ranking_item(c, s, trend), trend))
    items.sort(key=lambda x: x[1])
    return [item for item, _ in items[:limit]]

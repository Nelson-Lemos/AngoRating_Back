from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.score import CompanyScore
from app.models.ranking import ScoreHistory
from app.models.review import Review


WEIGHTS = {
    "quality": 0.20,
    "service": 0.20,
    "price": 0.15,
    "reliability": 0.25,
    "experience": 0.20,
}


def _calculate_confidence(total_reviews: int) -> str:
    if total_reviews >= 100:
        return "HIGH"
    elif total_reviews >= 30:
        return "MEDIUM"
    return "LOW"


def recalculate_score(db: Session, company_id: str) -> CompanyScore:
    reviews = db.query(Review).filter(
        Review.company_id == company_id,
        Review.is_valid == True,
    ).all()

    if not reviews:
        score_obj = db.query(CompanyScore).filter(CompanyScore.company_id == company_id).first()
        if not score_obj:
            score_obj = CompanyScore(company_id=company_id)
            db.add(score_obj)
        score_obj.score = 0.0
        score_obj.quality_score = 0.0
        score_obj.service_score = 0.0
        score_obj.price_score = 0.0
        score_obj.reliability_score = 0.0
        score_obj.experience_score = 0.0
        score_obj.total_reviews = 0
        score_obj.confidence_level = "LOW"
        score_obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(score_obj)
        return score_obj

    n = len(reviews)
    avg_quality = sum(r.quality for r in reviews) / n
    avg_service = sum(r.service for r in reviews) / n
    avg_price = sum(r.price for r in reviews) / n
    avg_reliability = sum(r.reliability for r in reviews) / n
    avg_experience = sum(r.experience for r in reviews) / n

    weighted_avg = (
        avg_quality * WEIGHTS["quality"]
        + avg_service * WEIGHTS["service"]
        + avg_price * WEIGHTS["price"]
        + avg_reliability * WEIGHTS["reliability"]
        + avg_experience * WEIGHTS["experience"]
    )

    score_0_100 = round(weighted_avg / 5 * 100, 1)

    score_obj = db.query(CompanyScore).filter(CompanyScore.company_id == company_id).first()
    if not score_obj:
        score_obj = CompanyScore(company_id=company_id)
        db.add(score_obj)

    score_obj.score = score_0_100
    score_obj.quality_score = round(avg_quality / 5 * 100, 1)
    score_obj.service_score = round(avg_service / 5 * 100, 1)
    score_obj.price_score = round(avg_price / 5 * 100, 1)
    score_obj.reliability_score = round(avg_reliability / 5 * 100, 1)
    score_obj.experience_score = round(avg_experience / 5 * 100, 1)
    score_obj.total_reviews = n
    score_obj.confidence_level = _calculate_confidence(n)
    score_obj.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(score_obj)

    history = ScoreHistory(
        company_id=company_id,
        score=score_0_100,
        total_reviews=n,
    )
    db.add(history)
    db.commit()

    return score_obj


def get_company_score(db: Session, company_id: str):
    return db.query(CompanyScore).filter(CompanyScore.company_id == company_id).first()


def get_score_history(db: Session, company_id: str, limit: int = 12):
    return (
        db.query(ScoreHistory)
        .filter(ScoreHistory.company_id == company_id)
        .order_by(ScoreHistory.created_at.desc())
        .limit(limit)
        .all()
    )

from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.models.review import Review
from app.models.company import Company
from app.schemas.review import ReviewCreate


def validate_review(db: Session, user_id: str, data: ReviewCreate, allow_update: bool = False) -> None:
    company = db.query(Company).filter(
        Company.id == data.company_id, Company.is_active == True
    ).first()
    if not company:
        raise ValueError("Empresa não encontrada")

    if not allow_update:
        existing = db.query(Review).filter(
            Review.user_id == user_id,
            Review.company_id == data.company_id,
            Review.is_valid == True,
        ).first()
        if existing:
            raise ValueError("Já avaliou esta empresa")

    recent_count = db.query(Review).filter(
        Review.user_id == user_id,
        Review.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
    ).count()
    if recent_count >= 20:
        raise ValueError("Limite de avaliações atingido (20 por dia)")


def create_review(db: Session, user_id: str, data: ReviewCreate) -> Review:
    validate_review(db, user_id, data)
    review = Review(
        user_id=user_id,
        company_id=data.company_id,
        quality=data.quality,
        service=data.service,
        price=data.price,
        reliability=data.reliability,
        experience=data.experience,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def update_review(db: Session, user_id: str, company_id: str, data: ReviewCreate) -> Review:
    """Permite re-avaliar: actualiza a avaliação existente em vez de recusar."""
    review = db.query(Review).filter(
        Review.user_id == user_id,
        Review.company_id == company_id,
        Review.is_valid == True,
    ).first()
    if not review:
        raise ValueError("Não encontrou uma avaliação sua para actualizar")

    review.quality = data.quality
    review.service = data.service
    review.price = data.price
    review.reliability = data.reliability
    review.experience = data.experience
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


def get_company_reviews(db: Session, company_id: str, skip: int = 0, limit: int = 20):
    query = db.query(Review).filter(Review.company_id == company_id, Review.is_valid == True)
    total = query.count()
    items = query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    return total, items


def get_user_reviews(db: Session, user_id: str, skip: int = 0, limit: int = 20):
    query = db.query(Review).filter(Review.user_id == user_id)
    total = query.count()
    items = query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    return total, items

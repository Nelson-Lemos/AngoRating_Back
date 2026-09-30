from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import hashlib

from app.models.fraud import FraudSignal
from app.models.review import Review


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()


def check_review_allowed(db: Session, user_id: str, company_id: str, ip: str = None, user_agent: str = None) -> dict:
    issues = []

    existing = db.query(Review).filter(
        Review.user_id == user_id,
        Review.company_id == company_id,
        Review.is_valid == True,
    ).first()
    if existing:
        issues.append("DUPLICATE_REVIEW")

    recent_count = db.query(Review).filter(
        Review.user_id == user_id,
        Review.created_at >= datetime.now(timezone.utc) - timedelta(hours=1),
    ).count()
    if recent_count >= 5:
        issues.append("HIGH_FREQUENCY")

    return {"allowed": len(issues) == 0, "issues": issues}


def record_fraud_signal(
    db: Session,
    user_id: str,
    company_id: str,
    signal_type: str,
    review_id: str = None,
    ip: str = None,
    user_agent: str = None,
):
    signal = FraudSignal(
        user_id=user_id,
        company_id=company_id,
        review_id=review_id,
        ip_hash=_hash_ip(ip) if ip else None,
        user_agent=user_agent,
        signal_type=signal_type,
    )
    db.add(signal)
    db.commit()
    return signal

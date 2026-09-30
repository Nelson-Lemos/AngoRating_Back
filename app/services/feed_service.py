from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta, timezone
import random

from app.models.review import Review
from app.models.company import Company
from app.models.score import CompanyScore
from app.models.user import User
from app.models.ranking import ScoreHistory


def get_feed(db: Session, limit: int = 20) -> dict:
    recent_reviews = (
        db.query(Review)
        .filter(Review.is_valid == True)
        .order_by(Review.created_at.desc())
        .limit(limit)
        .all()
    )
    reviews_payload = [
        {
            "id": r.id,
            "user_name": r.user.name if r.user else "Anónimo",
            "company_id": r.company_id,
            "company_name": r.company.name if r.company else "Empresa",
            "quality": r.quality,
            "service": r.service,
            "price": r.price,
            "reliability": r.reliability,
            "experience": r.experience,
            "created_at": r.created_at,
        }
        for r in recent_reviews
    ]

    battle = get_active_battle(db)
    wave = get_active_wave(db)

    return {
        "recent_reviews": reviews_payload,
        "battle": battle,
        "wave": wave,
    }


def get_active_battle(db: Session):
    from app.services.ranking_service import get_top_ranking

    rows = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews > 0)
        .order_by(desc(CompanyScore.score))
        .limit(4)
        .all()
    )
    if len(rows) < 2:
        return None

    pair = random.sample(rows, 2)
    (ca, sa), (cb, sb) = pair

    one = max(sa.total_reviews, 1)
    two = max(sb.total_reviews, 1)
    votes_a = one
    votes_b = two

    return {
        "id": f"battle-{ca.id[:6]}-{cb.id[:6]}",
        "title": "Quem tem melhor reputação?",
        "company_a_id": ca.id,
        "company_a_name": ca.name,
        "company_a_score": sa.score,
        "company_b_id": cb.id,
        "company_b_name": cb.name,
        "company_b_score": sb.score,
        "votes_a": votes_a * 37,
        "votes_b": votes_b * 29,
        "total_votes": (votes_a * 37) + (votes_b * 29),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d"),
    }


def get_active_wave(db: Session):
    peers = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(Company.is_active == True, CompanyScore.total_reviews > 0)
        .order_by(desc(CompanyScore.score))
        .limit(5)
        .all()
    )
    if not peers:
        return None

    top_company = peers[0]
    category = top_company[0].category

    same_category = [p for p in peers if p[0].category_id == top_company[0].category_id]
    if len(same_category) < 2:
        same_category = peers[:3]

    total_votes = 0
    company_votes = []
    for c, s in same_category[:3]:
        v = max(s.total_reviews, 1) * random.randint(20, 90)
        company_votes.append({
            "company_id": c.id,
            "company_name": c.name,
            "votes": v,
        })
        total_votes += v

    for item in company_votes:
        item["percentage"] = round((item["votes"] / total_votes) * 100, 1)

    category_name = category.name if category else ""
    return {
        "id": f"wave-{top_company[0].category_id[:6]}",
        "title": f"Qual é a melhor empresa de {category_name} em Angola?" if category_name else "Qual é a melhor empresa de Angola?",
        "description": "Vote na empresa que merece o título desta semana.",
        "company_votes": company_votes,
        "total_votes": total_votes,
        "ends_at": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d"),
    }


def get_leaderboard(db: Session, limit: int = 10) -> list:
    rows = (
        db.query(
            User.id.label("user_id"),
            User.name.label("user_name"),
            func.count(Review.id).label("total_reviews"),
        )
        .join(Review, Review.user_id == User.id)
        .filter(Review.is_valid == True)
        .group_by(User.id, User.name)
        .order_by(desc(func.count(Review.id)))
        .limit(limit)
        .all()
    )
    items = []
    for i, row in enumerate(rows, start=1):
        total_xp = row.total_reviews * 10
        items.append({
            "user_id": row.user_id,
            "user_name": row.user_name,
            "total_xp": total_xp,
            "level": _level_for_xp(total_xp),
            "total_reviews": row.total_reviews,
            "rank": i,
        })
    return items


def _level_for_xp(xp: int) -> str:
    if xp >= 5000:
        return "Top Reviewer"
    if xp >= 2000:
        return "Especialista"
    if xp >= 500:
        return "Crítico"
    if xp >= 100:
        return "Avaliador"
    return "Novato"


def get_challenges(db: Session, user_id: str) -> list:
    today = datetime.now(timezone.utc)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_iso = today.strftime("%Y-W%W")

    since_monday = (
        db.query(func.count(Review.id))
        .filter(
            Review.user_id == user_id,
            Review.is_valid == True,
            Review.created_at >= week_start,
            Review.created_at <= week_end,
        )
        .scalar()
    ) or 0

    total_reviews = (
        db.query(func.count(Review.id))
        .filter(Review.user_id == user_id, Review.is_valid == True)
        .scalar()
    ) or 0

    challenges = [
        {
            "id": f"ch-1-{week_iso}",
            "type": "rate_this_week",
            "description": "Avalie 3 empresas esta semana",
            "target": 3,
            "current": min(since_monday, 3),
            "xp_reward": 50,
            "completed": since_monday >= 3,
            "week_iso": week_iso,
        },
        {
            "id": f"ch-2-{week_iso}",
            "type": "reach_milestone",
            "description": "Avalie 5 empresas no total",
            "target": 5,
            "current": min(total_reviews, 5),
            "xp_reward": 40,
            "completed": total_reviews >= 5,
            "week_iso": week_iso,
        },
        {
            "id": f"ch-3-{week_iso}",
            "type": "explore_sectors",
            "description": "Avalie empresas de pelo menos 2 sectores",
            "target": 2,
            "current": _distinct_categories(db, user_id),
            "xp_reward": 35,
            "completed": _distinct_categories(db, user_id) >= 2,
            "week_iso": week_iso,
        },
    ]
    return challenges


def _distinct_categories(db: Session, user_id: str) -> int:
    return (
        db.query(func.count(func.distinct(Company.category_id)))
        .join(Review, Review.company_id == Company.id)
        .filter(Review.user_id == user_id, Review.is_valid == True)
        .scalar()
    ) or 0
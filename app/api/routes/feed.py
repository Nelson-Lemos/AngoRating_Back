from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.services import feed_service

router = APIRouter(prefix="/api/v1", tags=["Feed"])


@router.get("/feed")
def get_feed(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return feed_service.get_feed(db, limit)


@router.get("/waves/active")
def get_active_wave(db: Session = Depends(get_db)):
    return feed_service.get_active_wave(db)


@router.get("/gamification/leaderboard")
def get_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return {"items": feed_service.get_leaderboard(db, limit)}


@router.get("/gamification/challenges")
def get_challenges(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return {"items": feed_service.get_challenges(db, current_user.id)}


@router.get("/gamification/popular")
def get_popular_companies(
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
):
    from app.services.ranking_service import get_top_ranking
    items = get_top_ranking(db, limit=limit)
    return {"items": [i.model_dump() for i in items]}


@router.get("/gamification/me")
def get_my_gamification(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    from sqlalchemy import func
    from app.models.review import Review

    total_reviews = (
        db.query(func.count(Review.id))
        .filter(Review.user_id == current_user.id, Review.is_valid == True)
        .scalar()
    ) or 0

    total_xp = total_reviews * 10

    from app.services.feed_service import _level_for_xp
    level = _level_for_xp(total_xp)

    badges = []
    if total_reviews >= 1:
        badges.append({
            "type": "first_review",
            "name": "Primeira avaliação",
            "description": "Você fez a sua primeira avaliação",
            "icon": "🏅",
            "earned_at": None,
        })
    if total_reviews >= 5:
        badges.append({
            "type": "active_reviewer",
            "name": "Avaliador ativo",
            "description": "Você fez 5 avaliações",
            "icon": "⚡",
            "earned_at": None,
        })
    if total_reviews >= 10:
        badges.append({
            "type": "community_voice",
            "name": "Voz da Comunidade",
            "description": "Você fez 10 avaliações",
            "icon": "🇦🇴",
            "earned_at": None,
        })

    return {
        "total_xp": total_xp,
        "level": level,
        "next_level": None,
        "xp_to_next": None,
        "badges": badges,
        "rank_percentile": min(total_reviews * 10, 100),
        "total_reviews": total_reviews,
    }
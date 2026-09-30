"""Feed de activity.

O ficheiro anterior tinha três funções de gamificação — `get_active_battle`,
`get_active_wave` e `get_leaderboard` — que fabricavam os seus próprios
números:

* batalha: `votes_a = total_reviews * 37` — os votos eram o número de
  avaliações multiplicado por uma constante;
* wave: `random.randint(20, 90)` por entidade, e a percentagem derivada disso;
* leaderboard: `total_xp = total_reviews * 10` e níveis "Top Reviewer".

Nada disto reflectia nada que tivesse acontecido. As três foram removidas e
`/api/v1/feed/challenges` deixou de existir.

O que fica é o que é útil e verificável: avaliações recentes reais, entidades
que precisam de mais vozes, e o progresso privado de quem avalia.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.review import Review
from app.models.user import User
from app.services import trust_service


def get_feed(
    db: Session,
    limit: int = 20,
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
) -> dict:
    """Actividade recente. Só entra `PUBLISHED` e `is_valid`."""
    query = (
        db.query(Review)
        .join(Company, Company.id == Review.company_id)
        .filter(
            Review.is_valid == True,
            Review.status == "PUBLISHED",
            Company.is_active == True,
        )
    )
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)

    reviews = query.order_by(Review.created_at.desc()).limit(limit).all()

    return {
        "recent_reviews": [_review_payload(db, r) for r in reviews],
        "needs_reviews": needs_reviews(db, limit=6),
    }


def _review_payload(db: Session, r: Review) -> dict:
    company = r.company
    user = r.user
    return {
        "id": r.id,
        "rating": r.effective_rating(),
        "comment": r.comment,
        "criteria": r.criteria_dict(),
        "created_at": r.created_at,
        "user": (
            {
                "id": user.id,
                "name": user.name,
                "username": user.username,
                "reputation": user.reviewer_trust,
                "level": trust_service._level(user.reviewer_trust),
            }
            if user
            else None
        ),
        "company": (
            {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "kind": company.kind,
                "verification_status": company.verification_status,
            }
            if company
            else None
        ),
        "photo_count": r.photo_count,
        "comment_count": r.comment_count,
    }


def needs_reviews(db: Session, limit: int = 6) -> list[dict]:
    """Entidades com poucas avaliações — convém ao utilizador avaliá-las.

    Não é gamificação: é a lista do que ainda não tem voz na comunidade.
    """
    rows = (
        db.query(Company)
        .filter(
            Company.is_active == True,
            Company.status == "PUBLISHED",
        )
        .order_by(Company.review_count.asc(), Company.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "review_count": c.review_count,
            "category_name": c.category.name if c.category else None,
            "location_name": c.location.name if c.location else None,
        }
        for c in rows
        if c.review_count < 5
    ]


def get_contributors(db: Session, limit: int = 10) -> list[dict]:
    """Quem mais contribuiu, a sério.

    Ordena por avaliações publicadas, mostra a taxa de aprovação e o nível de
    reputação. Sem XP e sem níveis inventados — a diferença é visível.
    """
    rows = (
        db.query(User)
        .join(Review, Review.user_id == User.id)
        .filter(
            Review.is_valid == True,
            Review.status == "PUBLISHED",
            User.is_active == True,
        )
        .group_by(User.id)
        .order_by(desc(func.count(Review.id)))
        .limit(limit)
        .all()
    )

    items = []
    for i, user in enumerate(rows, start=1):
        data = trust_service.trust(db, user)
        items.append(
            {
                "rank": i,
                "user_id": user.id,
                "name": user.name,
                "username": user.username,
                "total_reviews": data["total_reviews"],
                "approved_contributions": data["approved_contributions"],
                "approval_rate": data["approval_rate"],
                "reputation": data["score"],
                "level": data["level"],
            }
        )
    return items


def get_my_progress(db: Session, user_id: str) -> dict:
    """Progresso privado de quem avalia. Sem comparação com os outros.

    Antes isto era `get_challenges()`: "Avalie 3 empresas esta semana, +50 XP".
    A pressão de gamificação sobre um utilizador a avaliar um banco pela
    primeira vez é o contrário do que queremos. O que fica é uma lista do que
    já contribuiu e do estado das avaliações em curso.
    """
    from app.models.media import Media
    from app.models.moderation import Contribution

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return {}

    reviews = (
        db.query(Review)
        .filter(Review.user_id == user_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    published = [r for r in reviews if r.is_valid and r.status == "PUBLISHED"]
    pending = [r for r in reviews if r.status == "PENDING"]

    contributions = (
        db.query(Contribution).filter(Contribution.user_id == user_id).all()
    )
    photos = (
        db.query(func.count(Media.id))
        .filter(Media.user_id == user_id, Media.status == "APPROVED")
        .scalar()
    ) or 0

    data = trust_service.trust(db, user)

    return {
        "reviews": {
            "total": len(reviews),
            "published": len(published),
            "pending": len(pending),
            "rejected": data["rejected_reviews"],
            "edited": sum(1 for r in reviews if r.edited_count),
        },
        "contributions": {
            "total": len(contributions),
            "approved": data["approved_contributions"],
            "rejected": data["rejected_contributions"],
        },
        "photos_approved": photos,
        "reputation": {
            "score": data["score"],
            "level": data["level"],
            "open_signals": data["open_signals"],
        },
        "last_30_days": _reviews_last_30_days(db, user_id),
    }


def _reviews_last_30_days(db: Session, user_id: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    return (
        db.query(func.count(Review.id))
        .filter(Review.user_id == user_id, Review.created_at >= since)
        .scalar()
    ) or 0

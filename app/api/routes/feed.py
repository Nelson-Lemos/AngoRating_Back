"""Rotas de feed.

Endpoints removidos (o frontend tem de ser actualizado — deixariam de
funcionar):
  * `GET /api/v1/waves/active`
  * `GET /api/v1/gamification/leaderboard`
  * `GET /api/v1/gamification/challenges`
  * `GET /api/v1/gamification/popular`
  * `GET /api/v1/gamification/me`

Todos os cinco serviam números calculados a partir de multiplicadores
(`total_reviews * 10` de XP, `total_reviews * 37` de votos, `rank_percentile`
inventado) e não de dados reais.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.services import feed_service

router = APIRouter(prefix="/api/v1", tags=["Feed"])


@router.get("/feed")
def get_feed(
    limit: int = Query(20, ge=1, le=50),
    category_id: str | None = None,
    location_id: str | None = None,
    db: Session = Depends(get_db),
):
    return feed_service.get_feed(db, limit, category_id, location_id)


@router.get("/contributors")
def get_contributors(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Quem mais contribuiu, ordenado por avaliações publicadas."""
    return {"items": feed_service.get_contributors(db, limit)}


@router.get("/me/progress")
def get_my_progress(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Contribuições do utilizador autenticado. Privado, sem competição."""
    return feed_service.get_my_progress(db, current_user.id)

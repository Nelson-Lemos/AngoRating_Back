"""Rankings honestos.

O código antigo tinha `top`, `trending`, `rising` e `declining`, todos derivados
de `score_history` — uma tabela de 95 linhas geradas com `random.uniform()`. Os
números não significavam nada e a interface apresentava-os como facto.

Aqui há três rankings, e todos se apoiam só em avaliações reais:

* `rating`  — melhor média, com um piso mínimo de avaliações para não premiar
              quem tem uma review de 5 estrelas e mais nada;
* `volume`  — mais avaliadas;
* `recent`  — com avaliação mais recente. A data vem de `reviews.created_at`.

Nada de "tendência +12%", nada de posição que sobe porque o número anterior foi
inventado. Se não há histórico real, não há tendência.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.review import Review
from app.models.score import CompanyScore
from app.schemas.score import RankingItem

# Piso de avaliações para o ranking de média. Abaixo disto a média não diz
# nada — e a UI mostra "confiança baixa" em vez de fingir.
MIN_REVIEWS = 5

BOARDS = {
    "rating": "Melhor avaliadas",
    "volume": "Mais avaliadas",
    "recent": "Avaliação mais recente",
}


def _last_review_at(db: Session, company_ids: list[str]) -> dict[str, datetime]:
    if not company_ids:
        return {}
    rows = (
        db.query(Review.company_id, func.max(Review.created_at))
        .filter(Review.company_id.in_(company_ids), Review.is_valid == True)
        .group_by(Review.company_id)
        .all()
    )
    return {cid: ts for cid, ts in rows if ts is not None}


def _item(
    db: Session,
    company: Company,
    score: Optional[CompanyScore],
    last: Optional[datetime],
) -> RankingItem:
    return RankingItem(
        company_id=company.id,
        name=company.name,
        slug=company.slug,
        kind=company.kind,
        category_name=company.category.name if company.category else None,
        location_name=company.location.name if company.location else None,
        rating=round(score.rating, 2) if score else 0.0,
        score=round(score.score, 1) if score else 0.0,
        total_reviews=score.total_reviews if score else company.review_count,
        confidence_level=score.confidence_level if score else "LOW",
        verification_status=company.verification_status,
        last_review_at=last,
    )


def _base_query(
    db: Session,
    category_id: Optional[str],
    location_id: Optional[str],
    min_reviews: int,
):
    query = (
        db.query(Company, CompanyScore)
        .join(CompanyScore, CompanyScore.company_id == Company.id)
        .filter(
            Company.is_active == True,
            Company.status == "PUBLISHED",
            CompanyScore.total_reviews >= min_reviews,
        )
    )
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)
    return query


def board(
    db: Session,
    kind: str = "rating",
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = 20,
) -> tuple[list[RankingItem], int]:
    """Devolve (itens, total). `kind` inválido cai em `rating`."""
    kind = kind if kind in BOARDS else "rating"
    min_reviews = 1 if kind == "recent" else MIN_REVIEWS

    query = _base_query(db, category_id, location_id, min_reviews)

    if kind == "rating":
        # Desempate pelo número de avaliações: entre 4.8 com 6 reviews e 4.8
        # com 40, é honesto preferir o segundo.
        query = query.order_by(
            desc(CompanyScore.rating), desc(CompanyScore.total_reviews)
        )
    elif kind == "volume":
        query = query.order_by(
            desc(CompanyScore.total_reviews), desc(CompanyScore.rating)
        )
    else:  # recent
        rows = query.all()
        ids = [c.id for c, _ in rows]
        last = _last_review_at(db, ids)
        pairs = [(c, s) for c, s in rows if c.id in last]
        pairs.sort(key=lambda p: last[p[0].id], reverse=True)
        total = len(pairs)
        items = [_item(db, c, s, last[c.id]) for c, s in pairs[:limit]]
        for i, it in enumerate(items, start=1):
            it.rank = i
        return items, total

    total = query.count()
    rows = query.limit(limit).all()
    last = _last_review_at(db, [c.id for c, _ in rows])
    items = [_item(db, c, s, last.get(c.id)) for c, s in rows]
    for i, it in enumerate(items, start=1):
        it.rank = i
    return items, total


def note_for(kind: str) -> Optional[str]:
    """Texto que acompanha a lista, para a UI dizer o que está a ordenar."""
    return {
        "rating": f"Ordenado por média, a partir de {MIN_REVIEWS} avaliações reais.",
        "volume": "Ordenado pelo número de avaliações publicadas.",
        "recent": "Ordenado pela avaliação mais recente. A data vem das avaliações, não de um histórico gerado.",
    }.get(kind)


def reviews_in_last(db: Session, company_id: str, days: int = 30) -> int:
    """Quantas avaliações reais chegaram nos últimos `days` dias."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(func.count(Review.id))
        .filter(
            Review.company_id == company_id,
            Review.is_valid == True,
            Review.status == "PUBLISHED",
            Review.created_at >= since,
        )
        .scalar()
    ) or 0

"""Motor de pontuação.

Regra inegociável: **todos os números saem da tabela `reviews`**. Nada de
valores pré-definidos, nada de aleatório, nada de contadores à mão. Se uma
entidade tiver 9 avaliações, mostra 9 e a confiança é baixa — e a interface
diz isso.

`recalculate()` é a única função que escreve em `company_scores`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.constants import REVIEW_PUBLISHED
from app.models.category import DEFAULT_CRITERIA
from app.models.review import Review
from app.models.score import CompanyScore, ScoreHistory

# Limiares de confiança. Mostrados ao utilizador: é melhor dizer "baseado em
# 4 avaliações" do que apresentar 4.7 como se fosse um facto.
CONFIDENCE_HIGH = 30
CONFIDENCE_MEDIUM = 5

# Chaves legacy das colunas quality/service/... espelhadas em company_scores
LEGACY_KEYS = ("quality", "service", "price", "reliability", "experience")


def _criteria_for(db: Session, company_id: str) -> list[dict]:
    from app.models.company import Company

    company = db.query(Company).filter(Company.id == company_id).first()
    if company and company.category:
        return company.category.criteria_list()
    return DEFAULT_CRITERIA


def _normalise_weights(criteria: list[dict]) -> list[dict]:
    out = []
    for c in criteria:
        try:
            weight = float(c.get("weight", 0))
        except (TypeError, ValueError):
            weight = 0.0
        out.append({"key": str(c.get("key")), "label": str(c.get("label")), "weight": max(0.0, weight)})
    total = sum(c["weight"] for c in out)
    if total <= 0:
        for c in out:
            c["weight"] = 1 / len(out) if out else 0
    else:
        for c in out:
            c["weight"] = c["weight"] / total
    return out


def _confidence(total: int) -> str:
    if total >= CONFIDENCE_HIGH:
        return "HIGH"
    if total >= CONFIDENCE_MEDIUM:
        return "MEDIUM"
    return "LOW"


def _published_reviews(db: Session, company_id: str) -> list[Review]:
    return (
        db.query(Review)
        .filter(
            Review.company_id == company_id,
            Review.is_valid == True,
            Review.status == REVIEW_PUBLISHED,
        )
        .all()
    )


def recalculate(db: Session, company_id: str) -> CompanyScore:
    """Recalcula o agregado de uma entidade a partir das avaliações reais."""
    reviews = _published_reviews(db, company_id)
    criteria = _normalise_weights(_criteria_for(db, company_id))

    score_obj = (
        db.query(CompanyScore).filter(CompanyScore.company_id == company_id).first()
    )
    if score_obj is None:
        score_obj = CompanyScore(company_id=company_id)
        db.add(score_obj)

    if not reviews:
        score_obj.rating = 0.0
        score_obj.total_reviews = 0
        score_obj.score = 0.0
        score_obj.criteria = None
        score_obj.confidence_level = "LOW"
        for key in LEGACY_KEYS:
            setattr(score_obj, f"{key}_score", 0.0)
        db.commit()
        db.refresh(score_obj)
        _sync_review_count(db, company_id, 0)
        return score_obj

    # Média das estrelas principais — o número público ★ 4.7
    ratings = [r.effective_rating() for r in reviews if r.effective_rating() > 0]
    n = len(reviews)
    avg_rating = (sum(ratings) / len(ratings)) if ratings else 0.0

    # Média por critério, contando só quem preencheu esse critério
    criteria_payload: dict[str, dict] = {}
    weighted_sum = 0.0
    weighted_weight = 0.0
    for c in criteria:
        values = []
        for r in reviews:
            v = r.criteria_dict().get(c["key"])
            if isinstance(v, (int, float)) and 1 <= v <= 5:
                values.append(float(v))
            elif c["key"] in LEGACY_KEYS:
                legacy_v = getattr(r, c["key"], 0) or 0
                if 1 <= legacy_v <= 5:
                    values.append(float(legacy_v))
        if not values:
            continue
        avg = sum(values) / len(values)
        criteria_payload[c["key"]] = {
            "avg": round(avg, 2),
            "count": len(values),
            "weight": round(c["weight"], 4),
            "label": c["label"],
        }
        weighted_sum += avg * c["weight"]
        weighted_weight += c["weight"]

    # AngoScore ponderado 0–100, só sobre os critérios que existem
    score_0_100 = (
        round(weighted_sum / weighted_weight / 5 * 100, 1) if weighted_weight > 0 else 0.0
    )

    previous = (score_obj.rating, score_obj.total_reviews)

    score_obj.rating = round(avg_rating, 2)
    score_obj.total_reviews = n
    score_obj.score = score_0_100
    score_obj.criteria = json.dumps(criteria_payload, ensure_ascii=False) if criteria_payload else None
    score_obj.confidence_level = _confidence(n)
    for key in LEGACY_KEYS:
        entry = criteria_payload.get(key)
        setattr(score_obj, f"{key}_score", round(entry["avg"] / 5 * 100, 1) if entry else 0.0)

    db.commit()
    db.refresh(score_obj)

    # Histórico só quando o número muda — um score_history por avaliação cria
    # ruído e inventa tendência.
    if previous != (score_obj.rating, score_obj.total_reviews):
        db.add(
            ScoreHistory(
                company_id=company_id,
                score=score_obj.score,
                rating=score_obj.rating,
                total_reviews=score_obj.total_reviews,
            )
        )
        db.commit()

    _sync_review_count(db, company_id, n)
    return score_obj


def _sync_review_count(db: Session, company_id: str, total: int) -> None:
    from app.models.company import Company

    company = db.query(Company).filter(Company.id == company_id).first()
    if company is not None and company.review_count != total:
        company.review_count = total
        db.commit()


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


def criteria_breakdown(score: CompanyScore | None) -> list[dict]:
    """Critérios prontos para a API, já sem as chaves internas."""
    if score is None or not score.criteria:
        return []
    try:
        data = json.loads(score.criteria)
    except (ValueError, TypeError):
        return []
    return [
        {
            "key": key,
            "label": value.get("label", key),
            "avg": value.get("avg", 0),
            "count": value.get("count", 0),
            "weight": value.get("weight", 0),
        }
        for key, value in data.items()
    ]

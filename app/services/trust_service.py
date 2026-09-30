"""Reputação do avaliador (§27).

Ideia central: um utilizador novo não é proibido de avaliar — seria uma
pilhagem contra o produto. O que fazemos é **dar peso** às avaliações e
**registar** o que cheira mal, deixando a decisão final a um humano.

Cada comportamento suspeito soma peso a um sinal. O peso total é lido pela
moderação. Nada disto é escondido do utilizador: o perfil mostra a reputação.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.fraud import FraudSignal, ReviewerTrustSnapshot
from app.models.user import User

# Sinais e o peso que somam. Pesos altos = padrão grave.
SIGNAL_WEIGHTS: dict[str, int] = {
    "DUPLICATE_REVIEW": 2,
    "HIGH_FREQUENCY": 2,
    "ACCOUNT_TOO_NEW": 1,
    "IDENTICAL_TEXT": 3,
    "BURST_REVIEWS": 3,
    "SELF_REVIEW": 5,
    "SAME_DEVICE_MULTI_ACCOUNT": 4,
    "NEW_ACCOUNT_MASS_REVIEW": 4,
    "LINKED_ENTITY": 3,
}

# A partir deste total, o item aparece na fila de moderação em vez de ser
# aceite em silêncio.
REVIEW_FLAG_THRESHOLD = 4


def _hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def signal_types(user: User) -> list[str]:
    """Sinais que existem só por este utilizador, derivados do seu histórico."""
    out: list[str] = []
    now = datetime.now(timezone.utc)

    if user.last_review_at is None:
        age_days = (now - _aware(user.created_at)).days
        if age_days < settings.REVIEWER_NEW_ACCOUNT_DAYS:
            out.append("ACCOUNT_TOO_NEW")

    reviews = user.reviews
    if len(reviews) >= 8:
        days = max((now - _aware(r.created_at)).days, 0) or 1
        if len(reviews) / days > 20:
            out.append("BURST_REVIEWS")

    texts = [(r.comment or "").strip().lower() for r in reviews if r.comment]
    if len(texts) >= 5:
        seen: set[str] = set()
        duplicates = 0
        for t in texts:
            if t in seen:
                duplicates += 1
            seen.add(t)
        if duplicates >= 2:
            out.append("IDENTICAL_TEXT")

    return out


def _aware(value):
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def check_review(
    db: Session,
    user: User,
    company,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
    comment: str | None = None,
    criteria: dict | None = None,
) -> dict:
    """Avalia se a review pode ser publicada.

    Devolve `{"allowed": bool, "issues": [...], "held_for_review": bool}`.
    `held_for_review` = o conteúdo é aceite mas vai para moderação, em vez de
    ser descartado. É um comportamento mais honesto do que bloquear.
    """
    issues: list[str] = []

    from app.models.review import Review

    already = (
        db.query(Review)
        .filter(
            Review.user_id == user.id,
            Review.company_id == company.id,
            Review.is_valid == True,
        )
        .first()
    )
    if already is not None:
        issues.append("DUPLICATE_REVIEW")

    window_1h = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = (
        db.query(func.count(Review.id))
        .filter(Review.user_id == user.id, Review.created_at >= window_1h)
        .scalar()
        ) or 0
    if recent >= 5:
        issues.append("HIGH_FREQUENCY")

    window_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    today = (
        db.query(func.count(Review.id))
        .filter(Review.user_id == user.id, Review.created_at >= window_24h)
        .scalar()
    ) or 0
    if today >= settings.REVIEW_DAILY_LIMIT:
        issues.append("DAILY_LIMIT")    # Proprietário da entidade a avaliar-se a si próprio: conflito de interesse.
    if company.owner_id and company.owner_id == user.id:
        issues.append("SELF_REVIEW")

    issues.extend(signal_types(user))

    if comment:
        text = comment.strip().lower()
        same_text = (
            db.query(func.count(Review.id))
            .filter(
                Review.user_id == user.id,
                func.lower(Review.comment) == text,
            )
            .scalar()
        ) or 0
        if same_text >= 2:
            if "IDENTICAL_TEXT" not in issues:
                issues.append("IDENTICAL_TEXT")

    # Vários SIGNAL_WEIGHTS acima do limiar ⇒ passa, mas vai para a fila.
    weight = sum(SIGNAL_WEIGHTS.get(i, 1) for i in issues if i != "DUPLICATE_REVIEW")
    held = weight >= REVIEW_FLAG_THRESHOLD

    # Reavaliar não é criar uma segunda review — por isso DUPLICATE_REVIEW
    # não é bloqueante aqui; a rota trata-o como actualização.
    blocking = [i for i in issues if i in ("DAILY_LIMIT", "SELF_REVIEW")]

    return {
        "allowed": len(blocking) == 0,
        "blocking": blocking,
        "issues": issues,
        "held_for_review": held,
        "weight": weight,
        "ip_hash": _hash_ip(ip),
        "user_agent": (user_agent or "")[:500] or None,
    }


def record_signal(
    db: Session,
    user_id: str,
    company_id: str,
    signal_type: str,
    *,
    review_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    detail: str | None = None,
) -> FraudSignal:
    signal = FraudSignal(
        user_id=user_id,
        company_id=company_id,
        review_id=review_id,
        signal_type=signal_type,
        weight=SIGNAL_WEIGHTS.get(signal_type, 1),
        ip_hash=_hash_ip(ip),
        user_agent=(user_agent or "")[:500] or None,
        detail=detail,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def open_signal_count(db: Session, user_id: str) -> int:
    return (
        db.query(func.count(FraudSignal.id))
        .filter(FraudSignal.user_id == user_id, FraudSignal.resolved == "OPEN")
        .scalar()
    ) or 0


def trust(db: Session, user: User) -> dict:
    """Reputação de um avaliador, calculada do que aconteceu de facto."""
    from app.models.moderation import Contribution
    from app.models.review import Review

    approved = (
        db.query(func.count(Review.id))
        .filter(
            Review.user_id == user.id,
            Review.is_valid == True,
            Review.status == "PUBLISHED",
        )
        .scalar()
    ) or 0
    rejected = (
        db.query(func.count(Review.id))
        .filter(
            Review.user_id == user.id,
            (Review.is_valid == False) | (Review.status.in_(["REJECTED", "SUSPENDED"])),
        )
        .scalar()
    ) or 0
    contributions = (
        db.query(func.count(Contribution.id))
        .filter(Contribution.user_id == user.id, Contribution.status == "APPROVED")
        .scalar()
    ) or 0
    rejected_contributions = (
        db.query(func.count(Contribution.id))
        .filter(Contribution.user_id == user.id, Contribution.status == "REJECTED")
        .scalar()
    ) or 0
    open_signals = open_signal_count(db, user.id)

    decided = approved + rejected
    approval_rate = (approved / decided) if decided else None

    # Reputação = volume de atividade que passou por um humano, corrigido pela
    # taxa de aprovação e penalizado por sinais abertos.
    # aprovação e penalizado por sinais abertos.
    raw = approved * 1.0 + contributions * 2.0
    if approval_rate is not None:
        raw *= approval_rate
    raw -= open_signals * 3
    raw = max(0.0, raw)

    score = int(round(min(100.0, raw * 4)))
    level = _level(score)

    return {
        "score": score,
        "level": level,
        "total_reviews": approved,
        "approved_reviews": approved,
        "rejected_reviews": rejected,
        "approved_contributions": contributions,
        "rejected_contributions": rejected_contributions,
        "open_signals": open_signals,
        "approval_rate": round(approval_rate * 100, 1) if approval_rate is not None else None,
    }


def _level(score: int) -> str:
    if score >= 80:
        return "TRUSTED"
    if score >= 50:
        return "ESTABLISHED"
    if score >= 20:
        return "ACTIVE"
    return "NEW"


def snapshot(db: Session, user: User) -> ReviewerTrustSnapshot:
    data = trust(db, user)
    row = ReviewerTrustSnapshot(
        user_id=user.id,
        total_reviews=data["total_reviews"],
        approved_reviews=data["approved_reviews"],
        rejected_reviews=data["rejected_reviews"],
        approved_contributions=data["approved_contributions"],
        open_fraud_signals=data["open_signals"],
        trust=float(data["score"]),
        level=data["level"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

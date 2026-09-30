"""Fila de moderação (§16).

Um único caminho para decidir: `decide()`. Toda a fila — entidade, imagem,
avaliação, denúncia, sugestão, verificação — entra por `enqueue()` e sai por
`decide()`. Assim o moderador aprende um botão e o dashboard conta tudo igual.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import (
    MOD_APPROVED, MOD_NEEDS_FIX, MOD_PENDING, MOD_REJECTED, MOD_SUSPENDED,
)
from app.models.moderation import ModerationItem

DECISIONS = (MOD_APPROVED, MOD_REJECTED, MOD_NEEDS_FIX, MOD_SUSPENDED)


def enqueue(
    db: Session,
    *,
    type: str,
    ref_id: str,
    submitted_by=None,
    entity_id: str | None = None,
    reason: str | None = None,
    origin: str = "WEB",
    priority: str = "NORMAL",
    status: str = MOD_PENDING,
) -> ModerationItem:
    """Coloca um item na fila. Ignora duplicados ainda pendentes."""
    existing = (
        db.query(ModerationItem)
        .filter(
            ModerationItem.type == type,
            ModerationItem.ref_id == ref_id,
            ModerationItem.status == MOD_PENDING,
        )
        .first()
    )
    if existing is not None:
        return existing

    item = ModerationItem(
        type=type,
        ref_id=ref_id,
        entity_id=entity_id,
        submitted_by=getattr(submitted_by, "id", None),
        submitted_by_name=getattr(submitted_by, "name", None),
        reason=reason,
        origin=origin,
        priority=priority,
        status=status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def decide(
    db: Session,
    item_id: str,
    decision: str,
    decided_by=None,
    note: str | None = None,
) -> ModerationItem:
    """Aplica uma decisão. Devolve o item actualizado.

    A decisão só é aceite a partir de `PENDING` — uma fila já decidida não
    volta a abrir sem uma nova submissão.
    """
    if decision not in DECISIONS:
        raise ValueError(f"Decisão inválida: {decision}")

    item = db.query(ModerationItem).filter(ModerationItem.id == item_id).first()
    if item is None:
        raise ValueError("Item de moderação não encontrado.")
    if item.status != MOD_PENDING:
        raise ValueError("Este item já foi decidido.")

    item.status = decision
    item.decided_by = getattr(decided_by, "id", None)
    item.decided_by_name = getattr(decided_by, "name", None)
    item.decided_at = datetime.now(timezone.utc)
    item.note = (note or "")[:2000] or None
    db.commit()
    db.refresh(item)
    return item


def queue(
    db: Session,
    *,
    type: str | None = None,
    status: str | None = MOD_PENDING,
    skip: int = 0,
    limit: int = 25,
) -> tuple[int, list[ModerationItem]]:
    q = db.query(ModerationItem)
    if type:
        q = q.filter(ModerationItem.type == type)
    if status:
        q = q.filter(ModerationItem.status == status)
    total = q.count()
    items = (
        q.order_by(ModerationItem.created_at.desc()).offset(skip).limit(limit).all()
    )
    return total, items


def counts(db: Session) -> dict[str, int]:
    """Contagem por tipo, só do que está pendente. É o que o dashboard mostra."""
    rows = (
        db.query(ModerationItem.type, func.count(ModerationItem.id))
        .filter(ModerationItem.status == MOD_PENDING)
        .group_by(ModerationItem.type)
        .all()
    )
    return {t: c for t, c in rows}


def summary(item: ModerationItem) -> dict:
    """Resumo serializável de um item da fila, sem JOINs."""
    return {
        "id": item.id,
        "type": item.type,
        "ref_id": item.ref_id,
        "entity_id": item.entity_id,
        "author": item.submitted_by_name,
        "author_id": item.submitted_by,
        "reason": item.reason,
        "origin": item.origin,
        "status": item.status,
        "priority": item.priority,
        "note": item.note,
        "created_at": item.created_at,
        "decided_at": item.decided_at,
        "decided_by": item.decided_by_name,
    }


def describe(db: Session, item: ModerationItem) -> dict:
    """Igual a `summary()` mas acrescenta uma descrição do conteúdo, para o
    moderador decidir sem abrir outra página."""
    from app.models.company import Company
    from app.models.media import Media
    from app.models.moderation import Contribution, VerificationRequest
    from app.models.report import Report
    from app.models.review import Review

    out = summary(item)
    title: str | None = None
    subtitle: str | None = None

    if item.type == "MEDIA":
        media = db.query(Media).filter(Media.id == item.ref_id).first()
        if media is not None:
            from app.services.media_service import url_for

            out["preview_url"] = url_for(media, width=320)
            out["media"] = {
                "id": media.id,
                "kind": media.kind,
                "source": media.source,
                "width": media.width,
                "height": media.height,
                "bytes": media.bytes,
                "position": media.position,
            }
            title = f"Imagem {media.kind.lower()}"
            if media.entity_id:
                company = db.query(Company).filter(Company.id == media.entity_id).first()
                title = company.name if company else title

    elif item.type == "ENTITY":
        company = db.query(Company).filter(Company.id == item.ref_id).first()
        if company is not None:
            from app.services.media_service import url_for_id

            title = company.name
            subtitle = company.description
            out["preview_url"] = url_for_id(db, company.main_media_id, width=320)
            out["entity"] = {
                "id": company.id,
                "slug": company.slug,
                "kind": company.kind,
                "status": company.status,
                "category_id": company.category_id,
                "location_id": company.location_id,
                "phone": company.phone,
            }

    elif item.type == "REVIEW":
        review = db.query(Review).filter(Review.id == item.ref_id).first()
        if review is not None:
            title = f"Avaliação de {review.effective_rating()}★"
            subtitle = (review.comment or "")[:280]
            company = review.company
            title = f"{title} · {company.name}" if company else title
            author = review.user
            out["author"] = out["author"] or (author.name if author else None)
            out["review"] = {
                "id": review.id,
                "rating": review.effective_rating(),
                "comment": review.comment,
                "criteria": review.criteria_dict(),
                "created_at": review.created_at,
            }

    elif item.type == "REPORT":
        report = db.query(Report).filter(Report.id == item.ref_id).first()
        if report is not None:
            subtitle = report.description
            review = report.review
            if review is not None:
                subtitle = (review.comment or "(sem comentário)")[:280]
                if review.company:
                    title = review.company.name
            out["report"] = {
                "reason": report.reason,
                "description": report.description,
            }

    elif item.type == "SUGGESTION":
        contrib = db.query(Contribution).filter(Contribution.id == item.ref_id).first()
        if contrib is not None:
            title = contrib.title
            try:
                payload = json.loads(contrib.payload)
            except (ValueError, TypeError):
                payload = {}
            subtitle = payload.get("description") or payload.get("proposed_changes", {}).get("description")
            out["contribution"] = {
                "kind": contrib.kind,
                "payload": payload,
            }

    elif item.type == "VERIFICATION":
        request = (
            db.query(VerificationRequest)
            .filter(VerificationRequest.id == item.ref_id)
            .first()
        )
        if request is not None:
            company = request.entity
            title = company.name if company else "Pedido de verificação"
            subtitle = request.evidence_note
            out["verification"] = {
                "status": request.status,
                "evidence_note": request.evidence_note,
                "evidence_media_id": request.evidence_media_id,
                "requested_at": request.created_at,
            }

    out["title"] = title
    out["subtitle"] = subtitle
    return out

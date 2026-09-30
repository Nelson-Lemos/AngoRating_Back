"""Registo de auditoria (§39).

Chamar `record` a partir das rotas administrativas. A função nunca levanta:
se a auditoria falhar, a acção de negócio tem de continuar. O problema é
registado no log da aplicação.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

logger = logging.getLogger("angorating.audit")


def client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def record(
    db: Session,
    *,
    actor=None,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    target_label: Optional[str] = None,
    result: str = "SUCCESS",
    request: Optional[Request] = None,
    detail: Optional[str] = None,
) -> None:
    from app.models.audit import AuditLog

    try:
        db.add(
            AuditLog(
                actor_id=getattr(actor, "id", None),
                actor_name=getattr(actor, "name", None),
                actor_role=getattr(actor, "role", None),
                action=action,
                target_type=target_type,
                target_id=target_id,
                target_label=target_label,
                result=result,
                ip=client_ip(request),
                user_agent=(request.headers.get("user-agent", "")[:500] if request else None),
                detail=detail,
            )
        )
        db.commit()
    except Exception:  # pragma: no cover - auditoria nunca pode travar o pedido
        db.rollback()
        logger.exception("Falha ao registar auditoria para %s", action)

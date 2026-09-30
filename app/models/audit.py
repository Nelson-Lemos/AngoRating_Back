from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Registo de acções administrativas (§39).

    Só de escrita — nunca se altera uma linha. Guarda quem, o quê, sobre o quê,
    com que resultado e de onde. É isto que torna a plataforma auditável.
    """

    __tablename__ = "audit_logs"

    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    actor_name = Column(String(120), nullable=True)
    actor_role = Column(String(20), nullable=True)

    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(40), nullable=True, index=True)
    target_id = Column(String(36), nullable=True, index=True)
    target_label = Column(String(200), nullable=True)

    result = Column(String(20), default="SUCCESS", nullable=False)

    ip = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)

    detail = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_recent", "created_at"),
        Index("ix_audit_target", "target_type", "target_id"),
    )

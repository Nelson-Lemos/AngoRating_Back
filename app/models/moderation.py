from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from app.core.constants import MOD_PENDING
from app.models.base import Base, UUIDMixin, TimestampMixin


class ModerationItem(Base, UUIDMixin, TimestampMixin):
    """Uma linha da fila de moderação (§16).

    A fila é polimórfica de propósito: `type` diz o que é e `ref_id` aponta
    para o registo concreto. Assim toda a moderação — entidade, imagem,
    avaliação, denúncia, sugestão, verificação — vive numa única fila, com um
    único caminho de decisão, e o dashboard conta tudo de uma vez.
    """

    __tablename__ = "moderation_items"

    type = Column(String(20), nullable=False, index=True)
    ref_id = Column(String(36), nullable=False, index=True)

    # Denormalizado para a fila não precisar de joins para se mostrar
    entity_id = Column(String(36), ForeignKey("companies.id"), nullable=True, index=True)
    submitted_by = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    submitted_by_name = Column(String(120), nullable=True)

    reason = Column(String(60), nullable=True)
    origin = Column(String(40), nullable=True)   # WEB / API / IMPORT

    status = Column(String(20), default=MOD_PENDING, nullable=False, index=True)
    priority = Column(String(10), default="NORMAL", nullable=False)

    decided_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    decided_by_name = Column(String(120), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_moderation_queue", "status", "type", "created_at"),
    )


class Contribution(Base, UUIDMixin, TimestampMixin):
    """Aporte da comunidade (§7).

    Um utilizador sugere uma entidade nova ou uma alteração a uma existente.
    Nunca publica directamente: entra em `PENDING` e só um administrador
    decide. O payload guarda o rascunho em JSON para podermos mostrar
    exactamente o que a pessoa escreveu.
    """

    __tablename__ = "contributions"

    kind = Column(String(30), nullable=False, index=True)

    entity_id = Column(
        String(36), ForeignKey("companies.id"), nullable=True, index=True
    )
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Nome do rascunho, para a fila mostrar sem abrir o payload
    title = Column(String(200), nullable=True)

    payload = Column(Text, nullable=False)

    status = Column(String(20), default=MOD_PENDING, nullable=False, index=True)
    moderation_item_id = Column(
        String(36), ForeignKey("moderation_items.id"), nullable=True
    )

    decided_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)

    # Entidade criada quando a contribuição foi aprovada
    resulting_entity_id = Column(
        String(36), ForeignKey("companies.id"), nullable=True
    )

    # `Contribution` tem duas FKs para `users` (autor e decisor).
    user = relationship("User", back_populates="contributions", foreign_keys=[user_id])
    decider = relationship("User", foreign_keys=[decided_by])
    entity = relationship("Company", foreign_keys=[entity_id])


class VerificationRequest(Base, UUIDMixin, TimestampMixin):
    """Pedido de selo de verificação (§17).

    O selo não é um interruptor: há pedido, evidência, análise e decisão. A
    interface mostra o estado do processo, não apenas um ícone.
    """

    __tablename__ = "verification_requests"

    entity_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(20), default="PENDING", nullable=False, index=True)

    # O que o requerente afirma e anexa como prova
    evidence_note = Column(Text, nullable=True)
    evidence_media_id = Column(
        String(36), ForeignKey("media.id"), nullable=True
    )

    # O que o administrador concluiu
    decision_note = Column(Text, nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    entity = relationship("Company", back_populates="verifications")
    requester = relationship("User", back_populates="verification_requests", foreign_keys=[requested_by])

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class FraudSignal(Base, UUIDMixin, TimestampMixin):
    """Sinal de comportamento suspeito (§27).

    Não bloqueia o utilizador: regista. O padrão é lido depois pelo
    moderador, que decide. O IP é guardado como hash — não precisamos do IP
    em claro para detectar dois accounts na mesma máquina.
    """

    __tablename__ = "fraud_signals"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    review_id = Column(String(36), ForeignKey("reviews.id"), nullable=True)

    signal_type = Column(String(50), nullable=False, index=True)
    weight = Column(Integer, default=1, nullable=False)

    ip_hash = Column(String(64), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)
    detail = Column(Text, nullable=True)

    resolved = Column(String(20), nullable=False, default="OPEN")
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class ReviewerTrustSnapshot(Base, UUIDMixin, TimestampMixin):
    """Fotografia diária da reputação de um avaliador.

    Serve para o gráfico de confiança do perfil e para justificar, de forma
    visível, por que uma avaliação antiga pesa mais do que uma de há dois
    minutos.
    """

    __tablename__ = "reviewer_trust_snapshots"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    total_reviews = Column(Integer, default=0, nullable=False)
    approved_reviews = Column(Integer, default=0, nullable=False)
    rejected_reviews = Column(Integer, default=0, nullable=False)
    approved_contributions = Column(Integer, default=0, nullable=False)
    open_fraud_signals = Column(Integer, default=0, nullable=False)

    trust = Column(Float, default=0.0, nullable=False)
    level = Column(String(20), default="NEW", nullable=False)

    user = relationship("User", back_populates="trust_snapshots")

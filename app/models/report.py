from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Report(Base, UUIDMixin, TimestampMixin):
    """Denúncia (§28). `status` alinha-se com a fila de moderação para que o
    dashboard conte denúncias por resolver sem lógica extra."""

    __tablename__ = "reports"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    review_id = Column(String(36), ForeignKey("reviews.id"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    reason = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(20), default="PENDING", nullable=False, index=True)
    resolved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(String(300), nullable=True)

    # Duas FKs para `users` (quem denuncia e quem resolve) — caminho explícito.
    user = relationship("User", back_populates="reports", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])
    review = relationship("Review", backref="reports")
    company = relationship("Company", backref="reports")

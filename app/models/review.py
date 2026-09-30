from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.core.constants import REVIEW_PUBLISHED
from app.models.base import Base, UUIDMixin, TimestampMixin, utcnow


class Review(Base, UUIDMixin, TimestampMixin):
    """Uma avaliação.

    `rating` (1–5) é a classificação principal que a pessoa escolhe primeiro
    (§19). `criteria` guarda os critérios específicos da categoria, em JSON
    ({chave: 1..5}) — foi por isto que `quality/service/price/...` viraram
    colunas legacy: as 125 avaliações já existentes continuam a contar.
    """

    __tablename__ = "reviews"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)

    # Classificação principal, 1–5. É o que aparece como ★ 4.7.
    rating = Column(Integer, nullable=True, index=True)

    # Critérios por categoria (§18): {"quality": 5, "ponctualidade": 4, ...}
    criteria = Column(Text, nullable=True)

    # Comentário opcional (§19). Antes não existia.
    comment = Column(Text, nullable=True)

    # Quando o autor teve a experiência. Separado de created_at porque uma
    # avaliação devisited de há 6 meses publicada hoje é informação relevante.
    visit_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(20), default=REVIEW_PUBLISHED, nullable=False, index=True)
    moderation_note = Column(String(500), nullable=True)
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Legado: cinco critérios fixos, mantidos em sincronia com `criteria`
    quality = Column(Integer, nullable=False, default=0)
    service = Column(Integer, nullable=False, default=0)
    price = Column(Integer, nullable=False, default=0)
    reliability = Column(Integer, nullable=False, default=0)
    experience = Column(Integer, nullable=False, default=0)

    # Legado: substituído por `status`. Mantido porque rotas antigas o leem.
    is_valid = Column(Boolean, default=True, nullable=False, index=True)

    # Contadores desnormalizados (evitam N+1 no feed e na página de entidade)
    helpful_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    photo_count = Column(Integer, default=0, nullable=False)

    edited_count = Column(Integer, default=0, nullable=False)
    last_edited_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reviews", foreign_keys=[user_id])
    moderator = relationship("User", foreign_keys=[reviewed_by])
    company = relationship("Company", back_populates="reviews")
    media = relationship(
        "Media", back_populates="review", cascade="all, delete-orphan"
    )

    @property
    def is_public(self) -> bool:
        return self.is_valid and self.status == REVIEW_PUBLISHED

    def criteria_dict(self) -> dict:
        import json

        if not self.criteria:
            return {}
        try:
            data = json.loads(self.criteria)
        except (ValueError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}

    def effective_rating(self) -> int:
        """A classificação principal; se ausente, derivada dos critérios."""
        if self.rating:
            return self.rating
        legacy = [self.quality, self.service, self.price, self.reliability, self.experience]
        filled = [v for v in legacy if v]
        if not filled:
            return 0
        return int(round(sum(filled) / len(filled)))

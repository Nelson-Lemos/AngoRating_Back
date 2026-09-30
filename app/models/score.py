from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, UUIDMixin, TimestampMixin, utcnow


class CompanyScore(Base, UUIDMixin, TimestampMixin):
    """Agregado de avaliação de uma entidade.

    `rating` (1–5) é o número público — ★ 4.7.
    `score` (0–100) é o AngoScore ponderado pelos critérios da categoria.

    Ambos são derivados exclusivamente da tabela `reviews`. Se `total_reviews`
    não bater certo com a contagem real, o agregado está errado.
    """

    __tablename__ = "company_scores"

    company_id = Column(
        String(36), ForeignKey("companies.id"), unique=True, nullable=False, index=True
    )

    # Público: média das estrelas, 1–5
    rating = Column(Float, default=0.0, nullable=False)
    total_reviews = Column(Integer, default=0, nullable=False)

    # AngoScore ponderado 0–100 (critérios da categoria)
    score = Column(Float, default=0.0, nullable=False)

    # Média por critério: {"quality": {"avg": 4.2, "count": 12}, ...}
    criteria = Column(Text, nullable=True)

    # Colunas legacy por critério (0–100), preenchidas por sincronia com
    # `criteria` para as rotas antigas continuarem a funcionar
    quality_score = Column(Float, default=0.0, nullable=False)
    service_score = Column(Float, default=0.0, nullable=False)
    price_score = Column(Float, default=0.0, nullable=False)
    reliability_score = Column(Float, default=0.0, nullable=False)
    experience_score = Column(Float, default=0.0, nullable=False)

    # LOW < 5 avaliações · MEDIUM < 30 · HIGH >= 30. Transparência: mostramos
    # quantas avaliações sustentam o número.
    confidence_level = Column(String(20), default="LOW", nullable=False)

    company = relationship("Company", back_populates="score")


class ScoreHistory(Base, UUIDMixin, TimestampMixin):
    """Ponto histórico do AngoScore. Só é escrito quando o valor muda de facto
    — nada de aleatório."""

    __tablename__ = "score_history"

    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    rating = Column(Float, default=0.0, nullable=False)
    total_reviews = Column(Integer, default=0, nullable=False)

    company = relationship("Company", back_populates="score_history")

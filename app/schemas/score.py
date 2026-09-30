"""Schemas de score.

Duas notas sobre o que **não** está aqui:

* `trend` — a antiga tendência vinha de `score_history` gerado aleatoriamente.
  Foi removida. A variação real é lida das avaliações com data, não de um
  inventário de números.
* `total_reviews` não é livre. `scoring_service` só o escreve contando linhas
  de `reviews`; a resposta da API reflecte sempre a contagem real.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CompanyScoreResponse(BaseModel):
    company_id: str
    rating: float = 0.0
    score: float = 0.0
    criteria: list[dict[str, Any]] = Field(default_factory=list)
    total_reviews: int = 0
    confidence_level: str = "LOW"
    confidence_label: Optional[str] = None
    updated_at: Optional[datetime] = None

    # Espelhos legados das 5 colunas antigas. Mantidos porque várias
    # colunas da tabela `company_scores` continuam lá e porque o frontend
    # legado lê estes campos.
    quality_score: float = 0.0
    service_score: float = 0.0
    price_score: float = 0.0
    reliability_score: float = 0.0
    experience_score: float = 0.0

    model_config = {"from_attributes": True}


class ScoreHistoryPoint(BaseModel):
    """Um ponto do gráfico de evolução. Só existe se o score mudou."""

    rating: float
    score: float
    total_reviews: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoreHistoryResponse(BaseModel):
    company_id: str
    points: list[ScoreHistoryPoint] = Field(default_factory=list)
    current: Optional[CompanyScoreResponse] = None


class RankingItem(BaseModel):
    """Uma linha de ranking. Só entra aqui o que é real."""

    company_id: str
    name: str
    slug: str
    kind: Optional[str] = None
    category_name: Optional[str] = None
    location_name: Optional[str] = None
    rating: float = 0.0
    score: float = 0.0
    total_reviews: int = 0
    confidence_level: str = "LOW"
    verification_status: Optional[str] = None
    last_review_at: Optional[datetime] = None
    rank: Optional[int] = None


class RankingResponse(BaseModel):
    board: str
    items: list[RankingItem] = Field(default_factory=list)
    total: int = 0
    note: Optional[str] = None

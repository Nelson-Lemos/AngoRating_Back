"""Endpoints de ranking.

Substituem `/top`, `/trending`, `/rising` e `/declining`. Os quatro devolviam
tendências calculadas sobre `score_history`, que era preenchido com números
aleatórios — `/trending`-promover uma empresa porque o inventário dizia que
tinha subido 0.4. Nenhum destes quatro existe agora; há um `/boards` só.

O frontend tem de ser actualizado: não há mais `/trending` para consumir.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.score import RankingResponse
from app.services import ranking_service

router = APIRouter(prefix="/api/v1/rankings", tags=["Rankings"])


@router.get("/boards", response_model=RankingResponse)
def list_boards(db: Session = Depends(get_db)):
    """Os rankings que existem, com o que cada um ordena de facto."""
    return {
        "boards": [
            {"id": key, "label": label, "note": ranking_service.note_for(key)}
            for key, label in ranking_service.BOARDS.items()
        ]
    }


@router.get("", response_model=RankingResponse)
@router.get("/board", response_model=RankingResponse, include_in_schema=False)
def get_board(
    board: str = Query("rating", description="rating | volume | recent"),
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = ranking_service.board(
        db, board, category_id, location_id, limit
    )
    return RankingResponse(
        board=board,
        items=items,
        total=total,
        note=ranking_service.note_for(board),
    )

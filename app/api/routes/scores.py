from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import scoring_service

router = APIRouter(prefix="/api/v1", tags=["Score"])


@router.get("/companies/{company_id}/score")
def get_score(company_id: str, db: Session = Depends(get_db)):
    score = scoring_service.get_company_score(db, company_id)
    if not score:
        raise HTTPException(status_code=404, detail="Score não encontrado")
    return {
        "company_id": score.company_id,
        "score": score.score,
        "quality_score": score.quality_score,
        "service_score": score.service_score,
        "price_score": score.price_score,
        "reliability_score": score.reliability_score,
        "experience_score": score.experience_score,
        "total_reviews": score.total_reviews,
        "confidence_level": score.confidence_level,
        "updated_at": score.updated_at,
    }


@router.get("/companies/{company_id}/history")
def get_history(company_id: str, db: Session = Depends(get_db)):
    history = scoring_service.get_score_history(db, company_id)
    return {
        "items": [
            {
                "id": h.id,
                "score": h.score,
                "total_reviews": h.total_reviews,
                "created_at": h.created_at,
            }
            for h in history
        ]
    }

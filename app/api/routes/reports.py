from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.schemas.report import ReportCreate
from app.models.report import Report

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.post("", response_model=dict, status_code=201)
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    report = Report(
        user_id=current_user.id,
        review_id=data.review_id,
        company_id=data.company_id,
        reason=data.reason,
        description=data.description,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": report.id, "message": "Denúncia registrada com sucesso"}

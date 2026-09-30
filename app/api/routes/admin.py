from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.company import Company
from app.models.review import Review
from app.models.report import Report
from app.models.category import Category
from app.models.location import Location
from app.models.score import CompanyScore

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return {
        "total_users": db.query(User).count(),
        "total_companies": db.query(Company).filter(Company.is_active == True).count(),
        "total_reviews": db.query(Review).filter(Review.is_valid == True).count(),
        "pending_reports": db.query(Report).filter(Report.status == "PENDING").count(),
        "total_categories": db.query(Category).count(),
        "total_locations": db.query(Location).count(),
    }


@router.get("/users")
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at}
            for u in users
        ],
    }


@router.put("/users/{user_id}/toggle-active")
def toggle_user_active(user_id: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.get("/reports")
def list_reports(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    query = db.query(Report)
    if status:
        query = query.filter(Report.status == status)
    total = query.count()
    reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id, "user_id": r.user_id, "review_id": r.review_id,
                "company_id": r.company_id, "reason": r.reason,
                "description": r.description, "status": r.status, "created_at": r.created_at,
            }
            for r in reports
        ],
    }


@router.put("/reviews/{review_id}/invalidate")
def invalidate_review(review_id: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    review.is_valid = False
    db.commit()
    return {"id": review.id, "is_valid": False}


@router.put("/reviews/{review_id}/restore")
def restore_review(review_id: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")
    review.is_valid = True
    db.commit()
    return {"id": review.id, "is_valid": True}


@router.put("/reports/{report_id}/resolve")
def resolve_report(report_id: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Denúncia não encontrada")
    report.status = "RESOLVED"
    db.commit()
    return {"id": report.id, "status": "RESOLVED"}

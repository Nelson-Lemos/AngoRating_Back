from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse, CompanyDetail
from app.services import company_service
from app.models.score import CompanyScore

router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])


@router.get("", response_model=dict)
def list_companies(
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total, items = company_service.list_companies(db, category_id, location_id, q, skip, limit)
    result = []
    for c in items:
        score_obj = db.query(CompanyScore).filter(CompanyScore.company_id == c.id).first()
        result.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "logo": c.logo,
            "category_id": c.category_id,
            "location_id": c.location_id,
            "category_name": c.category.name if c.category else None,
            "location_name": c.location.name if c.location else None,
            "is_verified": c.is_verified,
            "is_active": c.is_active,
            "score": score_obj.score if score_obj else 0.0,
            "total_reviews": score_obj.total_reviews if score_obj else 0,
            "confidence_level": score_obj.confidence_level if score_obj else "LOW",
            "created_at": c.created_at,
        })
    return {"total": total, "items": result}


@router.get("/{company_id}", response_model=dict)
def get_company(company_id: str, db: Session = Depends(get_db)):
    company = company_service.get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    score_obj = db.query(CompanyScore).filter(CompanyScore.company_id == company.id).first()
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
        "description": company.description,
        "logo": company.logo,
        "category_id": company.category_id,
        "location_id": company.location_id,
        "owner_id": company.owner_id,
        "category_name": company.category.name if company.category else None,
        "location_name": company.location.name if company.location else None,
        "is_verified": company.is_verified,
        "is_active": company.is_active,
        "score": score_obj.score if score_obj else 0.0,
        "total_reviews": score_obj.total_reviews if score_obj else 0,
        "confidence_level": score_obj.confidence_level if score_obj else "LOW",
        "quality_score": score_obj.quality_score if score_obj else 0.0,
        "service_score": score_obj.service_score if score_obj else 0.0,
        "price_score": score_obj.price_score if score_obj else 0.0,
        "reliability_score": score_obj.reliability_score if score_obj else 0.0,
        "experience_score": score_obj.experience_score if score_obj else 0.0,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
    }


@router.post("", response_model=dict, status_code=201)
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    company = company_service.create_company(db, data, owner_id=current_user.id)
    return {"id": company.id, "name": company.name, "slug": company.slug, "message": "Empresa criada com sucesso"}


@router.put("/{company_id}", response_model=dict)
def update_company(
    company_id: str,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    try:
        company = company_service.update_company(db, company_id, data, current_user.id)
        return {"id": company.id, "name": company.name, "message": "Empresa atualizada"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

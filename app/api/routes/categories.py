from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.category import Category
from app.models.location import Location
from app.schemas.category import CategoryResponse
from app.schemas.location import LocationResponse

router = APIRouter(prefix="/api/v1", tags=["Categories & Locations"])


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).filter(Category.is_active == True).all()
    return {"items": [{"id": c.id, "name": c.name, "slug": c.slug, "description": c.description} for c in cats]}


@router.get("/categories/{category_id}")
def get_category(category_id: str, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return {"id": cat.id, "name": cat.name, "slug": cat.slug, "description": cat.description}


@router.get("/locations")
def list_locations(db: Session = Depends(get_db)):
    locs = db.query(Location).filter(Location.type == "COUNTRY").all()
    result = []
    for loc in locs:
        provinces = db.query(Location).filter(Location.parent_id == loc.id, Location.type == "PROVINCE").all()
        result.append({
            "id": loc.id,
            "name": loc.name,
            "type": loc.type,
            "provinces": [{"id": p.id, "name": p.name} for p in provinces],
        })
    return {"items": result}

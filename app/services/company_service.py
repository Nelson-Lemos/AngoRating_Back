from sqlalchemy.orm import Session
from typing import Optional
import re

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def create_company(db: Session, data: CompanyCreate, owner_id: Optional[str] = None) -> Company:
    slug = _slugify(data.name)
    existing = db.query(Company).filter(Company.slug == slug).first()
    if existing:
        suffix = 2
        while db.query(Company).filter(Company.slug == f"{slug}-{suffix}").first():
            suffix += 1
        slug = f"{slug}-{suffix}"

    company = Company(
        name=data.name,
        slug=slug,
        description=data.description,
        logo=data.logo,
        category_id=data.category_id,
        location_id=data.location_id,
        owner_id=owner_id,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def get_company_by_id(db: Session, company_id: str) -> Optional[Company]:
    return db.query(Company).filter(Company.id == company_id, Company.is_active == True).first()


def get_company_by_slug(db: Session, slug: str) -> Optional[Company]:
    return db.query(Company).filter(Company.slug == slug, Company.is_active == True).first()


def list_companies(
    db: Session,
    category_id: Optional[str] = None,
    location_id: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
):
    query = db.query(Company).filter(Company.is_active == True)
    if category_id:
        query = query.filter(Company.category_id == category_id)
    if location_id:
        query = query.filter(Company.location_id == location_id)
    if q:
        query = query.filter(Company.name.ilike(f"%{q}%"))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return total, items


def update_company(db: Session, company_id: str, data: CompanyUpdate, user_id: str) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError("Empresa não encontrada")
    if company.owner_id != user_id:
        raise PermissionError("Sem permissão para editar esta empresa")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)
    if "name" in update_data:
        company.slug = _slugify(update_data["name"])
    db.commit()
    db.refresh(company)
    return company

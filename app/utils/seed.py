import uuid
import re
import random
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import User
from app.models.category import Category
from app.models.location import Location
from app.models.company import Company
from app.models.score import CompanyScore
from app.models.ranking import ScoreHistory
from app.models.review import Review


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        admin = db.query(User).filter(User.email == "admin@angorating.ao").first()
        if not admin:
            admin = User(
                id=str(uuid.uuid4()),
                name="Administrador",
                email="admin@angorating.ao",
                password_hash=get_password_hash("admin123"),
                role="ADMIN",
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            db.commit()
            print("Admin created: admin@angorating.ao / admin123")

        demo_user = db.query(User).filter(User.email == "user@angorating.ao").first()
        if not demo_user:
            demo_user = User(
                id=str(uuid.uuid4()),
                name="Utilizador Demo",
                email="user@angorating.ao",
                password_hash=get_password_hash("user123"),
                role="USER",
                is_active=True,
                is_verified=True,
            )
            db.add(demo_user)
            db.commit()
            print("Demo user created: user@angorating.ao / user123")

        categories_data = [
            ("Bancário", "bancario", "Instituições bancárias e financeiras"),
            ("Saúde", "saude", "Hospitais, clínicas e centros de saúde"),
            ("Educação", "educacao", "Escolas, universidades e instituições de ensino"),
            ("Tecnologia", "tecnologia", "Empresas de tecnologia e soluções digitais"),
            ("Hotelaria", "hotelaria", "Hotéis, pousadas e alojamento"),
            ("Restauração", "restauracao", "Restaurantes, cafés e gastronomia"),
            ("Telecomunicações", "telecomunicacoes", "Operadoras e serviços de telecomunicações"),
            ("Transportes", "transportes", "Transporte aéreo, terrestre e marítimo"),
            ("Energia", "energia", "Empresas de energia e combustíveis"),
            ("Retalho", "retalho", "Supermercados e cadeias de retalho"),
            ("Seguros", "seguros", "Empresas de seguros"),
            ("Público / Governo", "publico-governo", "Instituições públicas e governamentais"),
        ]
        cat_map = {}
        for name, slug, desc in categories_data:
            existing = db.query(Category).filter(Category.slug == slug).first()
            if not existing:
                cat = Category(id=str(uuid.uuid4()), name=name, slug=slug, description=desc)
                db.add(cat)
                cat_map[slug] = cat
            else:
                cat_map[slug] = existing
        db.commit()

        country = db.query(Location).filter(Location.name == "Angola", Location.type == "COUNTRY").first()
        if not country:
            country = Location(id=str(uuid.uuid4()), name="Angola", type="COUNTRY")
            db.add(country)
            db.commit()

        provinces_data = [
            "Bengo", "Benguela", "Bié", "Cabinda", "Cuando-Cubango",
            "Cuanza Norte", "Cuanza Sul", "Cunene", "Huambo", "Huíla",
            "Icolo e Bengo", "Luanda", "Lunda Norte", "Lunda Sul",
            "Malanje", "Moxico", "Namibe", "Uíge", "Zaire",
        ]
        prov_map = {}
        for pname in provinces_data:
            existing = db.query(Location).filter(Location.name == pname, Location.parent_id == country.id).first()
            if not existing:
                prov = Location(id=str(uuid.uuid4()), name=pname, type="PROVINCE", parent_id=country.id)
                db.add(prov)
                prov_map[pname] = prov
            else:
                prov_map[pname] = existing
        db.commit()

        luanda = prov_map.get("Luanda")
        benguela = prov_map.get("Benguela")

        demo_companies = [
            ("Banco BIC", "bancario", "Luanda", "Um dos maiores bancos privados de Angola."),
            ("Clínica Sagrada Esperança", "saude", "Luanda", "Clínica de referência em saúde privada."),
            ("Unitel", "telecomunicacoes", "Luanda", "Principal operadora de telecomunicações móveis."),
            ("Univ. Agostinho Neto", "educacao", "Luanda", "Principal universidade pública de Angola."),
            ("Hotel Presidente", "hotelaria", "Luanda", "Hotel 5 estrelas icónico de Luanda."),
            ("BFA", "bancario", "Luanda", "Banco de Fomento Angola."),
            ("Sonangol", "energia", "Luanda", "Empresa estatal petrolífera de Angola."),
            ("Restaurante Belmondo", "restauracao", "Luanda", "Restaurante de gastronomia internacional."),
            ("BAI", "bancario", "Luanda", "Banco Angolano de Investimentos."),
            ("Hotel Intercontinental", "hotelaria", "Luanda", "Hotel de luxo 5 estrelas referência em Luanda."),
            ("TAAG", "transportes", "Luanda", "Transportes Aéreos Angolanos."),
            ("Benguela Plaza", "hotelaria", "Benguela", "Hotel boutique na cidade de Benguela."),
            ("Kero", "retalho", "Luanda", "Cadeia de supermercados líder em Angola."),
            ("AfricaLink Tech", "tecnologia", "Luanda", "Startup de tecnologia e soluções digitais angolana."),
            ("ENSA", "seguros", "Luanda", "Empresa Nacional de Seguros e Resseguros de Angola."),
        ]

        company_scores = {
            "Banco BIC": {"score": 78, "q": 82, "s": 75, "p": 68, "r": 85, "e": 80, "reviews": 127},
            "Clínica Sagrada Esperança": {"score": 85, "q": 92, "s": 88, "p": 72, "r": 90, "e": 83, "reviews": 89},
            "Unitel": {"score": 62, "q": 65, "s": 55, "p": 58, "r": 70, "e": 62, "reviews": 312},
            "Univ. Agostinho Neto": {"score": 55, "q": 60, "s": 48, "p": 52, "r": 58, "e": 57, "reviews": 198},
            "Hotel Presidente": {"score": 88, "q": 90, "s": 91, "p": 78, "r": 92, "e": 89, "reviews": 76},
            "BFA": {"score": 72, "q": 74, "s": 70, "p": 65, "r": 78, "e": 73, "reviews": 145},
            "Sonangol": {"score": 48, "q": 50, "s": 42, "p": 45, "r": 55, "e": 48, "reviews": 203},
            "Restaurante Belmondo": {"score": 82, "q": 88, "s": 85, "p": 72, "r": 84, "e": 81, "reviews": 54},
            "BAI": {"score": 75, "q": 78, "s": 72, "p": 68, "r": 80, "e": 77, "reviews": 167},
            "Hotel Intercontinental": {"score": 91, "q": 94, "s": 93, "p": 82, "r": 95, "e": 91, "reviews": 94},
            "TAAG": {"score": 52, "q": 55, "s": 45, "p": 50, "r": 58, "e": 52, "reviews": 287},
            "Benguela Plaza": {"score": 79, "q": 82, "s": 80, "p": 74, "r": 82, "e": 78, "reviews": 38},
            "Kero": {"score": 84, "q": 86, "s": 82, "p": 80, "r": 88, "e": 84, "reviews": 256},
            "AfricaLink Tech": {"score": 87, "q": 90, "s": 88, "p": 82, "r": 86, "e": 90, "reviews": 42},
            "ENSA": {"score": 58, "q": 62, "s": 52, "p": 55, "r": 64, "e": 57, "reviews": 91},
        }

        companies_created = 0
        for name, cat_slug, prov_name, desc in demo_companies:
            existing = db.query(Company).filter(Company.name == name).first()
            if existing:
                continue
            cat = cat_map.get(cat_slug)
            prov = prov_map.get(prov_name)
            if not cat or not prov:
                continue
            company = Company(
                id=str(uuid.uuid4()),
                name=name,
                slug=_slugify(name),
                description=desc,
                category_id=cat.id,
                location_id=prov.id,
                owner_id=demo_user.id,
                is_verified=True,
                is_active=True,
            )
            db.add(company)
            db.flush()
            companies_created += 1

            sc = company_scores.get(name, {"score": 60, "q": 60, "s": 60, "p": 60, "r": 60, "e": 60, "reviews": 10})
            score_obj = CompanyScore(
                id=str(uuid.uuid4()),
                company_id=company.id,
                score=sc["score"],
                quality_score=sc["q"],
                service_score=sc["s"],
                price_score=sc["p"],
                reliability_score=sc["r"],
                experience_score=sc["e"],
                total_reviews=sc["reviews"],
                confidence_level="HIGH" if sc["reviews"] >= 100 else "MEDIUM" if sc["reviews"] >= 20 else "LOW",
            )
            db.add(score_obj)

            def score_to_stars(v):
                if v >= 90: return random.choice([4, 5, 5, 5])
                if v >= 75: return random.choice([3, 4, 4, 5])
                if v >= 60: return random.choice([3, 3, 4, 4])
                if v >= 40: return random.choice([2, 2, 3, 3])
                return random.choice([1, 1, 2, 2])

            for i in range(min(sc["reviews"], 8)):
                review = Review(
                    id=str(uuid.uuid4()),
                    user_id=demo_user.id,
                    company_id=company.id,
                    quality=score_to_stars(sc["q"]),
                    service=score_to_stars(sc["s"]),
                    price=score_to_stars(sc["p"]),
                    reliability=score_to_stars(sc["r"]),
                    experience=score_to_stars(sc["e"]),
                    is_valid=True,
                )
                db.add(review)

            for months_ago in range(6, 0, -1):
                hist = ScoreHistory(
                    id=str(uuid.uuid4()),
                    company_id=company.id,
                    score=max(0, sc["score"] + random.randint(-10, 10) - (6 - months_ago) * 2),
                    total_reviews=max(0, sc["reviews"] - months_ago * random.randint(5, 20)),
                )
                db.add(hist)

        db.commit()

        print("Seeds completed successfully!")
        print(f"Categories: {db.query(Category).count()}")
        print(f"Locations: {db.query(Location).count()}")
        print(f"Companies: {db.query(Company).count()}")
        print(f"Reviews: {db.query(Review).count()}")
        print(f"Scores: {db.query(CompanyScore).count()}")
        print(f"ScoreHistory: {db.query(ScoreHistory).count()}")
        print(f"Users: {db.query(User).count()}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()

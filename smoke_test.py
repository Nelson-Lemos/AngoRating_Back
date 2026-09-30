import os
import tempfile
import sys

# Use a temp SQLite DB to avoid touching the real one
tmpdir = tempfile.mkdtemp()
db_path = os.path.join(tmpdir, "smoke.db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.models.category import Category
from app.models.location import Location
from app.models.company import Company
from app.models.user import User

Base.metadata.create_all(bind=engine)

# Seed categories + locations + company directly
session = SessionLocal()
cat = Category(name="Telecomunicações", slug="telecomunicacoes", description="Operadores", is_active=True)
session.add(cat)
session.flush()
loc = Location(name="Luanda", type="PROVINCE")
session.add(loc)
session.flush()
company = Company(
    name="Unitel",
    slug="unitel-smoke",
    description="Operador móvel",
    category_id=cat.id,
    location_id=loc.id,
    is_active=True,
)
session.add(company)
session.commit()
company_id = company.id
cat_id = cat.id
loc_id = loc.id
session.close()

client = TestClient(app)


def step(name, cond):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}")
    if not cond:
        raise SystemExit(1)


# 1. register + login
r = client.post("/api/v1/auth/register", json={
    "name": "Nelson", "email": "nelson@angola.ao", "password": "secret123",
})
step("register user", r.status_code == 201)
r = client.post("/api/v1/auth/register", json={
    "name": "Maria", "email": "maria@angola.ao", "password": "secret123",
})
step("register user 2", r.status_code == 201)

r = client.post("/api/v1/auth/login", json={"email": "nelson@angola.ao", "password": "secret123"})
step("login nelson", r.status_code == 200)
t1 = r.json()["access_token"]

r = client.post("/api/v1/auth/login", json={"email": "maria@angola.ao", "password": "secret123"})
step("login maria", r.status_code == 200)
t2 = r.json()["access_token"]

h1 = {"Authorization": f"Bearer {t1}"}
h2 = {"Authorization": f"Bearer {t2}"}

# 2. company was seeded directly; verify it exists
r = client.get(f"/api/v1/companies/{company_id}")
step("company accessible", r.status_code == 200 and r.json()["name"] == "Unitel")

# 3. create review from nelson
r = client.post(f"/api/v1/companies/{company_id}/reviews", json={
    "company_id": company_id,
    "quality": 5, "service": 4, "price": 3, "reliability": 5, "experience": 4,
}, headers=h1)
if r.status_code != 201:
    print("  ->", r.status_code, r.text[:300])
step("create review", r.status_code == 201)
review_id = r.json()["id"]

# 4. agree/disagree from maria
r = client.post(f"/api/v1/reviews/{review_id}/agree", headers=h2)
step("agree with review", r.status_code == 200 and r.json()["agree_count"] == 1)

r = client.post(f"/api/v1/reviews/{review_id}/disagree", headers=h2)
step("flip to disagree", r.status_code == 200 and r.json()["agree_count"] == 0 and r.json()["disagree_count"] == 1)

r = client.get(f"/api/v1/reviews/{review_id}/stats", headers=h2)
step("vote stats", r.status_code == 200 and r.json()["user_vote"] is False)

# 5. comments
r = client.post(f"/api/v1/reviews/{review_id}/comments", json={"content": "Concordo plenamente"},
                headers=h2)
step("add comment", r.status_code == 200)
r = client.get(f"/api/v1/reviews/{review_id}/comments")
step("list comments", r.status_code == 200 and r.json()["total"] == 1)

# 6. notifications (nelson should have 1 - maria agreed... and commented)
r = client.get("/api/v1/notifications", headers=h1)
step("nelson notifications", r.status_code == 200 and len(r.json()["items"]) >= 1)
r = client.get("/api/v1/notifications/count", headers=h1)
step("unread count", r.status_code == 200)

# 7. battle vote
r = client.get("/api/v1/battles/active", headers=h1)
step("battle active", r.status_code == 200)
battle = r.json()
if battle:
    r = client.post("/api/v1/battles/vote", json={
        "company_a_id": battle["company_a_id"],
        "company_b_id": battle["company_b_id"],
        "voted_for": battle["company_a_id"],
    }, headers=h1)
    step("battle vote", r.status_code == 200 and r.json()["user_vote"] == battle["company_a_id"])
    r = client.get("/api/v1/battles/active", headers=h1)
    step("battle user_vote persisted", r.json()["user_vote"] == battle["company_a_id"])

# 8. company reviews include vote/comment counts
r = client.get(f"/api/v1/companies/{company_id}/reviews")
rv = r.json()["items"][0]
step("review counts in list", r.status_code == 200 and "agree_count" in rv and "comment_count" in rv)

# 9. re-rating (nelson updates)
r = client.post(f"/api/v1/companies/{company_id}/reviews", json={
    "company_id": company_id,
    "quality": 2, "service": 2, "price": 2, "reliability": 2, "experience": 2,
    "mode": "update",
}, headers=h1)
if r.status_code not in (200, 201):
    print("  ->", r.status_code, r.text[:300])
step("re-rate (update)", r.status_code in (200, 201) and r.json().get("mode") == "updated")

# 10. distribution
r = client.get(f"/api/v1/companies/{company_id}/reviews/distribution", headers=h1)
step("distribution", r.status_code == 200 and r.json()["user_vote"] is not None)

print("\n=== All smoke tests passed ===")
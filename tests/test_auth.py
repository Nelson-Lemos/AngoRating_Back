def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_user(client):
    response = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert data["role"] == "USER"


def test_register_duplicate_email(client):
    client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "dup@example.com",
        "password": "password123",
    })
    response = client.post("/api/v1/auth/register", json={
        "name": "Test User 2",
        "email": "dup@example.com",
        "password": "password456",
    })
    assert response.status_code == 409


def test_login(client):
    client.post("/api/v1/auth/register", json={
        "name": "Login User",
        "email": "login@example.com",
        "password": "password123",
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={
        "name": "Login User",
        "email": "wrong@example.com",
        "password": "password123",
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_token(client):
    client.post("/api/v1/auth/register", json={
        "name": "Me User",
        "email": "me@example.com",
        "password": "password123",
    })
    login = client.post("/api/v1/auth/login", json={
        "email": "me@example.com",
        "password": "password123",
    })
    token = login.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_create_category(client):
    from app.core.security import get_password_hash
    from app.core.database import SessionLocal
    from app.models.user import User
    import uuid

    db = SessionLocal()
    admin = User(
        id=str(uuid.uuid4()),
        name="Admin",
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        role="ADMIN",
    )
    db.add(admin)
    db.commit()

    login = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123",
    })
    token = login.json()["access_token"]

    response = client.get("/api/v1/categories", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    db.close()

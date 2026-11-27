from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.database.models import User
from app.main import app
import app.services.auth_security as security


def test_password_hash_and_signed_token(monkeypatch):
    monkeypatch.setattr(security, "SECRET_KEY", "x" * 48)
    encoded = security.hash_password("correct-horse-battery")
    assert security.verify_password("correct-horse-battery", encoded)
    assert not security.verify_password("wrong-password", encoded)
    token = security.create_access_token(17, "analyst")
    assert security.decode_access_token(token)["sub"] == "17"
    assert security.decode_access_token(token + "x") is None


def test_register_login_and_authenticated_me(monkeypatch):
    monkeypatch.setattr(security, "SECRET_KEY", "test-secret-key-that-is-long-enough-123456")
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(test_engine)
    factory = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.state.auth_disabled = False
    client = TestClient(app)
    payload = {"email": "analyst@example.com", "full_name": "Test Analyst", "password": "a-long-test-password"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409
    assert client.post("/api/auth/login", json={"email": payload["email"], "password": "wrong-password"}).status_code == 401
    login = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["role"] == "analyst"
    assert client.get("/api/dashboard/metrics").status_code == 401
    assert client.get("/api/dashboard/metrics", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    csv = "type,amount,nameOrig,nameDest\nTRANSFER,100,acct-a,acct-b\n"
    assert client.post("/api/dataset/upload", headers={"Authorization": f"Bearer {token}"},
                       files={"file": ("sample.csv", csv, "text/csv")}).status_code == 200
    with factory() as db:
        investigator = User(email="investigator@example.com", full_name="Investigator",
                             password_hash=security.hash_password("investigator-password"), role="investigator")
        db.add(investigator); db.commit(); db.refresh(investigator)
        investigator_token = security.create_access_token(investigator.id, investigator.role)
    denied = client.post("/api/dataset/upload", headers={"Authorization": f"Bearer {investigator_token}"},
                         files={"file": ("sample.csv", csv, "text/csv")})
    assert denied.status_code == 403
    client.close()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False
    test_engine.dispose()

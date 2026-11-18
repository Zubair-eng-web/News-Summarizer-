import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth
from app.core import models  # noqa: F401
from app.core import users
from app.core.config import settings
from app.core.database import Base


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(users, "ITERATIONS", 1000)
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(users, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def creds(email="ali@example.com", password="password123"):
    return {"email": email, "password": password}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me(client):
    r = client.post("/auth/register", json=creds())
    assert r.status_code == 201
    token = r.json()["access_token"]
    assert client.get("/me", headers=bearer(token)).json()["email"] == "ali@example.com"
    r = client.post("/auth/login", json=creds())
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"


def test_duplicate_and_bad_input(client):
    client.post("/auth/register", json=creds())
    assert client.post("/auth/register", json=creds()).status_code == 409
    assert client.post("/auth/register", json=creds(email="not-an-email")).status_code == 400
    assert client.post("/auth/register", json=creds(password="short")).status_code == 422


def test_wrong_password_and_missing_token(client):
    client.post("/auth/register", json=creds())
    assert client.post("/auth/login", json=creds(password="wrong-pass")).status_code == 401
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers=bearer("garbage")).status_code == 401


def test_my_interests(client):
    token = client.post("/auth/register", json=creds()).json()["access_token"]
    r = client.put("/me/interests", json={"interests": "AI, cricket"}, headers=bearer(token))
    assert r.json() == {"interests": ["ai", "cricket"]}
    assert client.get("/me", headers=bearer(token)).json()["interests"] == ["ai", "cricket"]


def test_accounts_disabled_without_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "")
    assert client.post("/auth/register", json=creds()).status_code == 503
    assert client.get("/me").status_code == 503
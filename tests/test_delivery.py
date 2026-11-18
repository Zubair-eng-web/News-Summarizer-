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


def register(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_delivery_requires_login(client):
    assert client.get("/me/delivery").status_code == 401
    assert client.put("/me/delivery", json={"digest_enabled": True}).status_code == 401


def test_default_off_then_toggle(client):
    a = register(client, "a@example.com")
    assert client.get("/me/delivery", headers=a).json() == {
        "email": "a@example.com",
        "digest_enabled": False,
        "telegram_chat_id": "",
        "digest_hour": None,
    }
    r = client.put("/me/delivery", json={"digest_enabled": True}, headers=a)
    assert r.json()["digest_enabled"] is True
    assert client.get("/me/delivery", headers=a).json()["digest_enabled"] is True
    r = client.put("/me/delivery", json={"digest_enabled": False}, headers=a)
    assert r.json()["digest_enabled"] is False


def test_only_opted_in_users_are_recipients(client):
    a = register(client, "a@example.com")
    register(client, "b@example.com")
    client.put("/me/interests", json={"interests": "ai"}, headers=a)
    client.put("/me/delivery", json={"digest_enabled": True}, headers=a)
    recipients = users.list_digest_recipients()
    assert [r["email"] for r in recipients] == ["a@example.com"]
    assert recipients[0]["interests"] == ["ai"]
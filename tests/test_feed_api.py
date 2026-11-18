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

STORIES = [
    {"title": "Budget talks", "summary": "", "priority": "Medium", "sources": []},
    {"title": "Cricket final", "summary": "", "priority": "Medium", "sources": []},
    {"title": "Quake", "summary": "", "priority": "Critical", "sources": []},
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(users, "ITERATIONS", 1000)
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(users, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    monkeypatch.setattr(auth, "get_recent_stories", lambda limit=100, **kw: list(STORIES))
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def register(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_feed_requires_login(client):
    assert client.get("/me/feed").status_code == 401


def test_two_users_get_different_feeds(client):
    a = register(client, "a@example.com")
    b = register(client, "b@example.com")
    client.put("/me/interests", json={"interests": "cricket"}, headers=a)

    feed_a = client.get("/me/feed", headers=a).json()
    feed_b = client.get("/me/feed", headers=b).json()
    assert [s["title"] for s in feed_a["stories"]] == ["Quake", "Cricket final", "Budget talks"]
    assert [s["title"] for s in feed_b["stories"]] == ["Quake", "Budget talks", "Cricket final"]
    assert feed_a["interests"] == ["cricket"] and feed_b["interests"] == []


def test_feed_limit(client):
    a = register(client, "a@example.com")
    assert client.get("/me/feed?limit=1", headers=a).json()["count"] == 1
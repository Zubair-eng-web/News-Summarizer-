import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth
from app.core import models  # noqa: F401
from app.core import user_sources as us
from app.core import users
from app.core.config import settings
from app.core.database import Base

FEED = {"kind": "rss", "url": "https://example.com/rss", "name": "Blog"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(users, "ITERATIONS", 1000)
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(users, "SessionLocal", factory)
    monkeypatch.setattr(us, "SessionLocal", factory)
    monkeypatch.setattr(us, "is_public_url", lambda url, resolver=None: "example.com" in url)
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def register(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_sources_require_login(client):
    assert client.get("/me/sources").status_code == 401
    assert client.post("/me/sources", json=FEED).status_code == 401
    assert client.delete("/me/sources/1").status_code == 401


def test_add_list_delete(client):
    a = register(client, "a@example.com")
    added = client.post("/me/sources", json=FEED, headers=a)
    assert added.status_code == 201 and added.json()["name"] == "Blog"
    listing = client.get("/me/sources", headers=a).json()
    assert listing["limit"] == us.MAX_PER_USER
    assert [s["name"] for s in listing["sources"]] == ["Blog"]
    source_id = added.json()["id"]
    assert client.delete(f"/me/sources/{source_id}", headers=a).json() == {"deleted": source_id}
    assert client.get("/me/sources", headers=a).json()["sources"] == []
    assert client.delete(f"/me/sources/{source_id}", headers=a).status_code == 404


def test_errors(client, monkeypatch):
    a = register(client, "a@example.com")
    assert client.post("/me/sources", json=FEED, headers=a).status_code == 201
    assert client.post("/me/sources", json=FEED, headers=a).status_code == 409
    bad = {**FEED, "url": "https://evil.test/rss"}
    assert client.post("/me/sources", json=bad, headers=a).status_code == 400
    assert client.post("/me/sources", json={**FEED, "kind": "podcast"}, headers=a).status_code == 422
    monkeypatch.setattr(us, "MAX_PER_USER", 1)
    other = {**FEED, "url": "https://example.com/other"}
    assert client.post("/me/sources", json=other, headers=a).status_code == 400


def test_users_cannot_touch_each_others_sources(client):
    a = register(client, "a@example.com")
    b = register(client, "b@example.com")
    source_id = client.post("/me/sources", json=FEED, headers=a).json()["id"]
    assert client.get("/me/sources", headers=b).json()["sources"] == []
    assert client.delete(f"/me/sources/{source_id}", headers=b).status_code == 404
    assert len(client.get("/me/sources", headers=a).json()["sources"]) == 1
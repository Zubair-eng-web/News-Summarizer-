import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth
from app.api import reads as reads_api
from app.core import models  # noqa: F401
from app.core import reads, users
from app.core.config import settings
from app.core.database import Base
from app.core.models import StoryDB


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
    monkeypatch.setattr(reads, "SessionLocal", factory)
    monkeypatch.setattr(reads, "init_db", lambda: None)
    with factory() as s:
        s.add(StoryDB(title="Story one", summary="x"))
        s.commit()
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(reads_api.router)
    return TestClient(app)


def token(client, email="ali@example.com"):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_mark_read_and_list(client):
    h = token(client)
    assert client.get("/me/reads", headers=h).json() == {"count": 0, "story_ids": []}
    r = client.put("/me/reads/1", headers=h)
    assert r.status_code == 200 and r.json()["created"] is True
    assert client.put("/me/reads/1", headers=h).json()["created"] is False
    assert client.get("/me/reads", headers=h).json() == {"count": 1, "story_ids": [1]}


def test_mark_unread(client):
    h = token(client)
    client.put("/me/reads/1", headers=h)
    assert client.delete("/me/reads/1", headers=h).json()["read"] is False
    assert client.delete("/me/reads/1", headers=h).status_code == 404
    assert client.get("/me/reads", headers=h).json()["story_ids"] == []


def test_unknown_story_and_no_login(client):
    h = token(client)
    assert client.put("/me/reads/999", headers=h).status_code == 404
    assert client.get("/me/reads").status_code == 401


def test_reads_are_per_user(client):
    a = token(client, "a@example.com")
    b = token(client, "b@example.com")
    client.put("/me/reads/1", headers=a)
    assert client.get("/me/reads", headers=b).json()["story_ids"] == []
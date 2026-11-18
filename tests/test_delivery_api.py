import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import user_digest
from app.api import auth
from app.core import models, users  # noqa: F401
from app.core.database import Base

STORIES = [{"title": "Quake", "summary": "", "priority": "Critical", "sources": []}]


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(users, "SessionLocal", sessionmaker(bind=engine))
    person = users.create_user("a@x.com", "password123")
    app = FastAPI()
    app.include_router(auth.router)
    app.dependency_overrides[auth.get_current_user] = lambda: person
    return TestClient(app)


def test_get_defaults(client):
    assert client.get("/me/delivery").json() == {
        "email": "a@x.com",
        "digest_enabled": False,
        "telegram_chat_id": "",
        "digest_hour": None,
    }


def test_put_all_fields_then_get(client):
    body = {"digest_enabled": True, "telegram_chat_id": "12345", "digest_hour": 18}
    assert client.put("/me/delivery", json=body).status_code == 200
    got = client.get("/me/delivery").json()
    assert got["digest_enabled"] is True
    assert got["telegram_chat_id"] == "12345" and got["digest_hour"] == 18


def test_partial_update_keeps_other_fields(client):
    client.put("/me/delivery", json={"telegram_chat_id": "777", "digest_hour": 6})
    got = client.put("/me/delivery", json={"digest_enabled": True}).json()
    assert got["digest_enabled"] is True
    assert got["telegram_chat_id"] == "777" and got["digest_hour"] == 6


def test_null_hour_clears_it(client):
    client.put("/me/delivery", json={"digest_hour": 6})
    got = client.put("/me/delivery", json={"digest_hour": None}).json()
    assert got["digest_hour"] is None


def test_invalid_values_rejected(client):
    assert client.put("/me/delivery", json={"telegram_chat_id": "abc def"}).status_code == 400
    assert client.put("/me/delivery", json={"digest_hour": 24}).status_code in (400, 422)


def test_hourly_job_skips_users_without_own_hour():
    people = [
        {"id": 1, "email": "a@x.com", "interests": []},
        {"id": 2, "email": "b@x.com", "interests": [], "digest_hour": 6},
    ]
    sent = []
    result = user_digest.send_user_digests(
        recipients=people,
        stories=STORIES,
        sender=lambda items, email: sent.append(email),
        already_sent=lambda uid, day: False,
        mark_sent=lambda uid, day: None,
        telegram=lambda chat, text: None,
        now_hour=7,
        today="2026-11-17",
        only_scheduled=True,
    )
    assert sent == ["b@x.com"]
    assert result == {"sent": 1, "skipped": 1, "failed": 0}

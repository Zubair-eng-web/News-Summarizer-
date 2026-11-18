import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.core.config import settings
from app.main import app

KEY = "secret-key-123"
HEADERS = {"X-API-Key": KEY}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(routes, "get_stats", lambda: {"ok": True})
    return TestClient(app)


def test_open_when_no_key_is_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    assert client.get("/stats").status_code == 200


def test_missing_key_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", KEY)
    assert client.get("/stats").status_code == 401


def test_wrong_key_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", KEY)
    assert client.get("/stats", headers={"X-API-Key": "nope"}).status_code == 401


def test_correct_key_is_accepted(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", KEY)
    response = client.get("/stats", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health_and_root_stay_open(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", KEY)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_job_triggers_need_key(client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "is_busy", lambda: False)
    monkeypatch.setattr(routes, "safe_run", lambda job, name: calls.append(name))
    monkeypatch.setattr(settings, "api_key", KEY)

    assert client.post("/run-digest").status_code == 401
    assert calls == []  # job shuru hi nahi hua

    assert client.post("/run-digest", headers=HEADERS).status_code == 200
    assert calls == ["Digest"]


def test_chat_needs_key(client, monkeypatch):
    seen = []
    monkeypatch.setattr(routes, "answer_question", lambda q: seen.append(q) or {"answer": "x", "sources": []})
    monkeypatch.setattr(settings, "api_key", KEY)
    assert client.post("/chat", json={"question": "hello"}).status_code == 401
    assert seen == []  # Gemini tak baat pahunchi hi nahi

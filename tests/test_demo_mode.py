import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.demo import add_demo_guard, is_blocked
from app.core.config import settings


@pytest.fixture
def client():
    app = FastAPI()
    add_demo_guard(app)

    @app.get("/stories")
    def stories():
        return {"ok": True}

    @app.post("/chat")
    def chat():
        return {"ok": True}

    @app.post("/run-digest")
    def digest():
        return {"ok": True}

    @app.post("/auth/register")
    def register():
        return {"ok": True}

    return TestClient(app)


def test_everything_works_when_demo_is_off(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.post("/run-digest").status_code == 200
    assert client.post("/auth/register").status_code == 200


def test_demo_blocks_writes_but_allows_reads_and_chat(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    assert client.get("/stories").status_code == 200
    assert client.post("/chat").status_code == 200
    assert client.post("/run-digest").status_code == 403
    assert client.post("/auth/register").status_code == 403


def test_is_blocked_rules():
    assert not is_blocked("GET", "/anything")
    assert not is_blocked("POST", "/research/")
    assert is_blocked("PUT", "/interests")
    assert is_blocked("DELETE", "/me/sources/1")
    assert is_blocked("POST", "/run-cleanup")
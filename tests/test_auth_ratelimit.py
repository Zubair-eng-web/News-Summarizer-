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
    monkeypatch.setattr(settings, "auth_rate_limit", 3)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(users, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def login(client, email="ali@example.com", headers=None):
    body = {"email": email, "password": "wrong-pass-1"}
    return client.post("/auth/login", json=body, headers=headers or {})


def test_login_limited_per_ip(client):
    for _ in range(3):
        assert login(client).status_code == 401
    blocked = login(client)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1


def test_login_limited_per_email_even_when_ip_changes(client, monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    for i in range(3):
        assert login(client, headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code == 401
    assert login(client, headers={"X-Forwarded-For": "10.0.0.99"}).status_code == 429
    other = login(client, email="other@example.com", headers={"X-Forwarded-For": "10.0.0.98"})
    assert other.status_code == 401


def test_register_limited_per_ip(client):
    codes = [
        client.post(
            "/auth/register", json={"email": f"u{i}@example.com", "password": "password123"}
        ).status_code
        for i in range(4)
    ]
    assert codes == [201, 201, 201, 429]


def test_rate_limit_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit", 0)
    assert all(login(client).status_code == 401 for _ in range(10))
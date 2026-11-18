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


def src(name, link="https://x.example/1"):
    return {"source": name, "link": link}


STORIES = [
    {"title": "Own", "summary": "", "priority": "Medium", "sources": [src("Mine (custom)")]},
    {"title": "Foreign", "summary": "", "priority": "Medium", "sources": [src("Theirs (custom)")]},
    {"title": "Builtin", "summary": "", "priority": "Medium", "sources": [src("BBC World")]},
    {
        "title": "Mixed",
        "summary": "",
        "priority": "Medium",
        "sources": [src("Theirs (custom)"), src("Dawn")],
    },
    {"title": "Nosrc", "summary": "", "priority": "Medium", "sources": []},
]


def public(host, port):
    return [(0, 0, 0, "", ("93.184.216.34", port))]


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(users, "ITERATIONS", 1000)
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    monkeypatch.setattr(settings, "auth_rate_limit", 0)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(users, "SessionLocal", factory)
    monkeypatch.setattr(us, "SessionLocal", factory)
    monkeypatch.setattr(auth, "get_recent_stories", lambda limit=100, **kw: list(STORIES))
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app), factory


def register(client, email):
    r = client.post("/auth/register", json={"email": email, "password": "password123"}).json()
    return r["user"]["id"], {"Authorization": "Bearer " + r["access_token"]}


def titles(response):
    return {s["title"] for s in response.json()["stories"]}


def test_scope_mine_hides_only_foreign_custom(env):
    client, factory = env
    a_id, a = register(client, "a@example.com")
    b_id, b = register(client, "b@example.com")
    us.add_source(a_id, "rss", "https://a.example/rss", "Mine", factory, public)
    us.add_source(b_id, "rss", "https://b.example/rss", "Theirs", factory, public)

    assert titles(client.get("/me/feed?scope=mine", headers=a)) == {
        "Own", "Builtin", "Mixed", "Nosrc"
    }
    assert titles(client.get("/me/feed?scope=mine", headers=b)) == {
        "Foreign", "Builtin", "Mixed", "Nosrc"
    }


def test_default_scope_shows_everything(env):
    client, _ = env
    _, a = register(client, "a@example.com")
    response = client.get("/me/feed", headers=a)
    assert len(titles(response)) == 5 and response.json()["scope"] == "all"


def test_invalid_scope_rejected(env):
    client, _ = env
    _, a = register(client, "a@example.com")
    assert client.get("/me/feed?scope=nope", headers=a).status_code == 422


def test_label_collision_gets_id_suffix(factory=None):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    f = sessionmaker(bind=engine, autoflush=False)
    first = us.add_source(1, "rss", "https://a.example/rss", "Blog", f, public)
    second = us.add_source(2, "rss", "https://b.example/rss", "Blog", f, public)
    assert us.own_source_labels(1, f) == {"Blog (custom)"}
    assert us.own_source_labels(2, f) == {f"Blog (custom #{second['id']})"}
    assert first["id"] != second["id"]


def test_same_url_means_same_label_for_both_owners():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    f = sessionmaker(bind=engine, autoflush=False)
    us.add_source(1, "rss", "https://a.example/rss", "Blog", f, public)
    us.add_source(2, "rss", "https://a.example/rss", "Other name", f, public)
    assert us.own_source_labels(1, f) == us.own_source_labels(2, f) == {"Blog (custom)"}

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import routes
from app.core import models  # noqa: F401
from app.core import storage
from app.core.database import Base
from app.core.models import ArticleDB
from app.core.story import Story
from app.main import app


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(storage, "SessionLocal", factory)
    monkeypatch.setattr(storage, "init_db", lambda: None)
    yield factory
    engine.dispose()


@pytest.fixture
def client():
    return TestClient(app)


def story(title, link, priority="High"):
    return Story(
        title=title,
        summary="Summary.",
        sources=[("BBC", link)],
        priority=priority,
        sentiment="neutral",
        credibility="Single source",
    )


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    assert client.get("/").status_code == 200


def test_stories_empty(client, temp_db):
    r = client.get("/stories")
    assert r.status_code == 200
    assert r.json() == {"count": 0, "stories": []}


def test_stories_returns_saved(client, temp_db):
    storage.save_stories([story("A", "http://x/a", "Critical")])
    data = client.get("/stories").json()
    assert data["count"] == 1
    first = data["stories"][0]
    assert first["title"] == "A"
    assert first["priority"] == "Critical"
    assert first["sources"] == [{"source": "BBC", "link": "http://x/a"}]


def test_stories_priority_filter(client, temp_db):
    storage.save_stories([story("A", "http://x/a", "Critical"), story("B", "http://x/b", "Low")])
    data = client.get("/stories?priority=low").json()  # chhote haroof bhi chalte hain
    assert [s["title"] for s in data["stories"]] == ["B"]


def test_stories_invalid_priority(client, temp_db):
    assert client.get("/stories?priority=Urgent").status_code == 400


def test_stories_limit_validation(client, temp_db):
    assert client.get("/stories?limit=0").status_code == 422


def test_stats_endpoint(client, temp_db):
    storage.save_stories([story("A", "http://x/a", "Critical")])
    data = client.get("/stats").json()
    assert data["stories"] == 1
    assert data["stories_by_priority"]["Critical"] == 1


def test_articles_endpoint(client, temp_db):
    with temp_db() as s:
        s.add(ArticleDB(title="T", link="http://x/1", summary="s", source="Dawn"))
        s.commit()
    data = client.get("/articles").json()
    assert data["count"] == 1
    assert data["articles"][0]["source"] == "Dawn"


def test_run_digest_starts_background_job(client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "is_busy", lambda: False)
    monkeypatch.setattr(routes, "safe_run", lambda job, name: calls.append(name))
    r = client.post("/run-digest")
    assert r.status_code == 200
    assert r.json() == {"status": "started", "job": "Digest"}
    assert calls == ["Digest"]


def test_run_alerts_starts_background_job(client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "is_busy", lambda: False)
    monkeypatch.setattr(routes, "safe_run", lambda job, name: calls.append(name))
    r = client.post("/run-alerts")
    assert r.json() == {"status": "started", "job": "Alert check"}
    assert calls == ["Alert check"]


def test_run_returns_409_when_busy(client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "is_busy", lambda: True)
    monkeypatch.setattr(routes, "safe_run", lambda job, name: calls.append(name))
    assert client.post("/run-digest").status_code == 409
    assert calls == []

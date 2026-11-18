from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors import rss
from app.collectors.rss import Article
from app.core import models  # noqa: F401
from app.core import oracle_stats, source_health
from app.core.database import Base


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)


def test_record_success_then_failure_keeps_last_ok(factory):
    source_health.record("Dawn", "rss", True, 5, factory=factory)
    source_health.record("Dawn", "rss", False, 0, "feed down", factory=factory)
    row = source_health.load_all(factory)["Dawn"]
    assert row["last_error"] == "feed down"
    assert row["last_ok"] is not None
    assert row["last_items"] == 0


def test_success_clears_error(factory):
    source_health.record("Dawn", "rss", False, 0, "boom", factory=factory)
    source_health.record("Dawn", "rss", True, 3, factory=factory)
    row = source_health.load_all(factory)["Dawn"]
    assert row["last_error"] == "" and row["last_items"] == 3


def test_record_never_raises():
    class Broken:
        def __call__(self):
            raise RuntimeError("db down")

    source_health.record("X", "rss", True, 1, factory=Broken())


def test_source_status_includes_health(factory):
    source_health.record("Dawn", "rss", False, 0, "blocked", factory=factory)
    out = oracle_stats.source_status(factory=factory, now=datetime(2026, 11, 18))
    dawn = next(s for s in out["sources"] if s["name"] == "Dawn")
    assert dawn["last_error"] == "blocked"
    assert dawn["last_checked"] is not None
    bbc = next(s for s in out["sources"] if s["name"] == "BBC World")
    assert bbc["last_error"] == "" and bbc["last_checked"] is None


def test_collect_all_records_each_feed(monkeypatch):
    calls = []
    monkeypatch.setattr(source_health, "record", lambda *a, **k: calls.append(a))

    def fake_fetch(source, url, limit=10):
        if source == "A":
            return [Article(title="t", link="l", summary="", source="A")]
        return []

    monkeypatch.setattr(rss, "fetch_feed", fake_fetch)
    monkeypatch.setattr(rss, "FEEDS", {"A": "u1", "B": "u2"})
    result = rss.collect_all(1, extra_feeds={})
    assert len(result) == 1
    assert calls[0][:4] == ("A", "rss", True, 1)
    assert calls[1][:3] == ("B", "rss", False)
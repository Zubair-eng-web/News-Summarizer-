from datetime import datetime, timedelta

import httpx
import pytest
import streamlit as st
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from app.api import oracle as oracle_api
from app.core import oracle_stats, runs
from app.core.database import Base
from app.core.models import AlertDB, ArticleDB, PipelineRunDB, StoryDB, VideoDB
from dashboard import api_client
from dashboard.oracle import status

NOW = datetime(2026, 11, 18, 12, 0, 0)


@pytest.fixture
def factory():
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    make = sessionmaker(bind=engine)
    with make() as s:
        s.add_all([
            StoryDB(title="Flood hits Sindh", summary="Rain floods villages.", priority="Critical",
                    sentiment="negative", created_at=NOW - timedelta(hours=1),
                    sources_json='[["Dawn", "https://d/1"], ["BBC World", "https://b/1"]]'),
            StoryDB(title="Flood relief continues in Sindh", summary="Aid arrives.",
                    priority="High", sentiment="neutral", created_at=NOW - timedelta(days=1),
                    sources_json='[["Dawn", "https://d/2"]]'),
            StoryDB(title="Old budget story", summary="Budget.", priority="Low",
                    sentiment="neutral", created_at=NOW - timedelta(days=100),
                    sources_json='[["Dawn", "https://d/3"]]'),
            VideoDB(video_id="abcdefghijk", title="Flood video", link="https://y/1",
                    channel="DW News", created_at=NOW - timedelta(hours=2)),
            ArticleDB(title="A1", link="https://d/1", source="Dawn",
                      collected_at=NOW - timedelta(hours=1)),
            ArticleDB(title="A2", link="https://b/1", source="BBC World",
                      collected_at=NOW - timedelta(days=10)),
            AlertDB(story_key="k1", title="Flood alert", sent_at=NOW - timedelta(hours=2)),
            AlertDB(story_key="k2", title="Old alert", sent_at=NOW - timedelta(hours=30)),
            PipelineRunDB(job="Digest", ok=True, started_at=NOW - timedelta(hours=3),
                          duration_ms=4000, detail="collect: 5"),
            PipelineRunDB(job="Alert check", ok=False, started_at=NOW - timedelta(hours=1),
                          error="boom"),
        ])
        s.commit()
    return make


def test_analytics(factory):
    out = oracle_stats.analytics(30, factory=factory, now=NOW)
    assert out["total_stories"] == 2 and out["total_videos"] == 1
    assert {"priority": "Critical", "stories": 1} in out["priority"]
    assert out["sources"][0] == {"source": "Dawn", "stories": 2, "critical": 1}
    assert [d["day"] for d in out["daily"]] == ["2026-11-17", "2026-11-18"]
    assert out["weekly"] == [{"week": "2026-11-16", "stories": 2, "critical": 1}]
    assert {"term": "flood", "count": 2} in out["trending"]
    assert {"category": "Disaster", "stories": 2} in out["categories"]
    assert out["video_channels"] == [{"channel": "DW News", "videos": 1}]
    assert oracle_stats.analytics(200, factory=factory, now=NOW)["total_stories"] == 3


def test_system_status(factory):
    out = oracle_stats.system_status(factory=factory)
    assert out["database"]["ok"] is True
    jobs = {j["job"]: j for j in out["jobs"]}
    assert jobs["Digest"]["last_ok"] is True and jobs["Digest"]["last_success"]
    assert jobs["Alert check"]["last_ok"] is False and jobs["Alert check"]["last_success"] is None
    assert out["recent_errors"][0]["error"] == "boom"
    assert out["alerts_total"] == 2
    assert isinstance(out["configured"]["ai"], bool)
    assert all(out["latest"].values())


def test_alert_history_and_runs(factory):
    out = oracle_stats.alert_history(10, factory=factory, now=NOW)
    assert out["total"] == 2 and out["last_24h"] == 1
    assert out["alerts"][0]["title"] == "Flood alert"
    rows = oracle_stats.recent_runs(5, factory=factory)
    assert rows[0]["job"] == "Alert check" and rows[0]["ok"] is False


def test_source_status(factory):
    out = oracle_stats.source_status(factory=factory, now=NOW)
    rows = {r["name"]: r for r in out["sources"]}
    assert rows["Dawn"]["status"] == "active" and rows["Dawn"]["items"] == 1
    assert rows["BBC World"]["status"] == "no_recent"
    assert rows["The Guardian"]["status"] == "no_data"
    assert rows["DW News"]["status"] == "active" and rows["DW News"]["kind"] == "youtube"
    assert out["total"] == len(out["sources"])


def test_record_and_track(factory, monkeypatch):
    runs.record("Weekly report", True, NOW, 1200, detail="ok", factory=factory)
    with factory() as s:
        assert s.query(PipelineRunDB).filter(PipelineRunDB.job == "Weekly report").count() == 1
    runs.record("Skipped", True, NOW, 1)  # no factory under pytest: must do nothing
    saved = []
    monkeypatch.setattr(runs, "record", lambda *a, **k: saved.append((a, k)))
    assert runs.track("Digest", lambda: {"trace": ["a", "b"]}) == {"trace": ["a", "b"]}
    assert saved[0][0][1] is True and saved[0][1]["detail"] == "a\nb"

    def boom():
        raise ValueError("bad")

    with pytest.raises(ValueError):
        runs.track("Digest", boom)
    assert saved[1][0][1] is False and "ValueError" in saved[1][1]["error"]


def test_safe_run_records(monkeypatch):
    from app import scheduler

    saved = []
    monkeypatch.setattr(runs, "record", lambda *a, **k: saved.append(a))
    monkeypatch.setattr(scheduler.error_alerts, "report", lambda *a, **k: None)
    assert scheduler.safe_run(lambda: None, "Videos") is True
    assert scheduler.safe_run(lambda: 1 / 0, "Videos") is False
    assert [s[1] for s in saved] == [True, False]


def test_oracle_endpoints(monkeypatch):
    for name in ("analytics", "system_status", "alert_history", "source_status"):
        monkeypatch.setattr(oracle_api.oracle_stats, name, lambda *a, **k: {"ok": True})
    monkeypatch.setattr(oracle_api.oracle_stats, "recent_runs",
                        lambda *a, **k: [{"job": "Digest"}])
    app = FastAPI()
    app.include_router(oracle_api.router)
    c = TestClient(app)
    assert c.get("/oracle/analytics?days=7").json() == {"ok": True}
    assert c.get("/oracle/analytics?days=0").status_code == 422
    assert c.get("/oracle/system").json() == {"ok": True}
    assert c.get("/oracle/alerts?limit=5").json() == {"ok": True}
    assert c.get("/oracle/alerts?limit=0").status_code == 422
    assert c.get("/oracle/sources").json() == {"ok": True}
    assert c.get("/oracle/runs").json() == {"count": 1, "runs": [{"job": "Digest"}]}


INFO = {
    "database": {"ok": True},
    "latest": {"story": "2026-11-18T09:00:00", "article": "2026-11-18T10:00:00", "video": None},
    "jobs": [{"job": "Digest", "last_run": "2026-11-18T07:00:00", "last_ok": True,
              "last_success": "2026-11-18T07:00:00", "runs": 3}],
    "recent_errors": [{"job": "Alert check", "at": "2026-11-17T07:00:00", "error": "boom"}],
    "configured": {"ai": True, "email": True, "telegram": False},
    "alerts_total": 2, "demo_mode": False, "debug": True,
}


def test_real_checks():
    checks = {c["label"]: c for c in status.build_real_checks(True, INFO, now=NOW)}
    assert checks["Database"]["state"] == "ok"
    assert checks["Collector (last article)"]["value"] == "2 h ago"
    assert checks["Scheduler (last job)"]["state"] == "ok"
    assert checks["Last digest"]["value"] == "OK, 5 h ago"
    assert checks["AI service"]["value"] == "API key configured"
    assert checks["Telegram"]["value"] == "Not configured"
    assert checks["Breaking alerts sent"]["value"] == "2"
    failed = dict(INFO, jobs=[{"job": "Digest", "last_run": "2026-11-18T07:00:00",
                               "last_ok": False, "last_success": None, "runs": 1}])
    out = {c["label"]: c for c in status.build_real_checks(False, failed, now=NOW)}
    assert out["Last digest"]["state"] == "bad" and out["API"]["state"] == "bad"
    empty = {c["label"]: c for c in status.build_real_checks(True, {}, now=NOW)}
    assert empty["Database"]["state"] == "bad"
    assert empty["Scheduler (last job)"]["value"] == "No runs recorded yet"


STORY = {"id": 1, "title": "Flood hits Sindh", "summary": "Rain.", "priority": "Critical",
         "sentiment": "negative", "credibility": "Single source", "category": "Disaster",
         "created_at": "2026-11-18T09:00:00",
         "sources": [{"source": "Dawn", "link": "https://d.example/1"}], "claims": []}
ANALYTICS = {
    "days": 30, "total_stories": 2, "total_videos": 1,
    "priority": [{"priority": "Critical", "stories": 1}, {"priority": "High", "stories": 1},
                 {"priority": "Medium", "stories": 0}, {"priority": "Low", "stories": 0}],
    "sentiment": [{"sentiment": "negative", "stories": 2}],
    "categories": [{"category": "Disaster", "stories": 2}],
    "sources": [{"source": "Dawn", "stories": 2, "critical": 1}],
    "daily": [{"day": "2026-11-17", "stories": 1, "critical": 0},
              {"day": "2026-11-18", "stories": 1, "critical": 1}],
    "weekly": [{"week": "2026-11-16", "stories": 2, "critical": 1}],
    "trending": [{"term": "flood", "count": 2}],
    "video_daily": [{"day": "2026-11-18", "videos": 1}],
    "video_channels": [{"channel": "DW News", "videos": 1}],
}
ALERTS = {"total": 2, "last_24h": 1, "alerts": [{"title": "Flood alert",
          "sent_at": "2026-11-18T09:00:00"}],
          "configured": {"ai": True, "email": True, "telegram": False}}
RUNS = {"count": 2, "runs": [
    {"job": "Digest", "ok": True, "started_at": "2026-11-18T07:00:00", "duration_ms": 4200,
     "error": "", "detail": "collect: 20 collected"},
    {"job": "Alert check", "ok": False, "started_at": "2026-11-18T08:00:00", "duration_ms": 100,
     "error": "boom", "detail": ""}]}
SOURCES = {"total": 2, "sources": [
    {"name": "Dawn", "kind": "rss", "builtin": True, "items": 5,
     "last_at": "2026-11-18T08:00:00", "status": "active"},
    {"name": "DW News", "kind": "youtube", "builtin": True, "items": 0,
     "last_at": None, "status": "no_data"}]}
ROUTES = {
    ("GET", "/health"): {"status": "ok", "debug": True},
    ("GET", "/stats"): {"articles": 9, "stories": 2, "alerts_sent": 2,
                        "stories_by_priority": {"Critical": 1, "High": 1, "Medium": 0, "Low": 0}},
    ("GET", "/stories"): {"count": 1, "stories": [STORY]},
    ("GET", "/videos"): {"count": 0, "videos": []},
    ("GET", "/oracle/analytics"): ANALYTICS,
    ("GET", "/oracle/system"): INFO,
    ("GET", "/oracle/alerts"): ALERTS,
    ("GET", "/oracle/runs"): RUNS,
    ("GET", "/oracle/sources"): SOURCES,
    ("GET", "/me/sources"): {"limit": 8, "sources": []},
}


def _install(monkeypatch, routes=None):
    routes = ROUTES if routes is None else routes

    def handler(request):
        body = routes.get((request.method, request.url.path))
        if body is None:
            return httpx.Response(404, json={"detail": "nf"})
        return httpx.Response(200, json=body)

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    st.cache_data.clear()


def _run(code, logged_in=False):
    at = AppTest.from_string(code, default_timeout=30)
    if logged_in:
        at.session_state["token"] = "t"
        at.session_state["user_email"] = "a@b.com"
    return at.run()


@pytest.mark.parametrize("func", ["analytics", "alerts", "sources", "system"])
def test_ops_pages_render(monkeypatch, func):
    _install(monkeypatch)
    assert not _run(f"from dashboard.oracle import ops\nops.{func}()").exception


def test_sources_logged_in(monkeypatch):
    _install(monkeypatch)
    assert not _run("from dashboard.oracle import ops\nops.sources()", logged_in=True).exception


def test_analytics_period_and_empty(monkeypatch):
    _install(monkeypatch)
    at = _run("from dashboard.oracle import ops\nops.analytics()")
    at.selectbox(key="an_days").select("Last 7 days").run()
    assert not at.exception
    empty = dict(ROUTES)
    empty[("GET", "/oracle/analytics")] = dict(ANALYTICS, total_stories=0, total_videos=0)
    _install(monkeypatch, empty)
    at = _run("from dashboard.oracle import ops\nops.analytics()")
    assert not at.exception


def test_overview_uses_real_status(monkeypatch):
    _install(monkeypatch)
    at = _run("from dashboard.oracle import overview\noverview.render()")
    assert not at.exception
    assert any("1 RSS + 1 YouTube" in m.value for m in at.markdown)
    assert any("Collector (last article)" in m.value for m in at.markdown)


def test_pages_fall_back_on_older_api(monkeypatch):
    old = {k: v for k, v in ROUTES.items() if not k[1].startswith("/oracle")}
    _install(monkeypatch, old)
    for func in ("overview.render", "ops.system", "ops.sources"):
        module = func.split(".")[0]
        at = _run(f"from dashboard.oracle import {module}\n{func}()")
        assert not at.exception
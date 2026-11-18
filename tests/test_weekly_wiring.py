import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.scheduler import run_weekly


@pytest.fixture
def client():
    return TestClient(app)


def test_run_weekly_calls_runner_and_returns_report():
    assert run_weekly(runner=lambda: {"total": 3}) == {"total": 3}


def test_weekly_endpoint_without_ai_by_default(client, monkeypatch):
    monkeypatch.setattr(
        routes,
        "build_weekly_report",
        lambda overview=False: {"total": 1, "overview": "x" if overview else ""},
    )
    assert client.get("/weekly").json() == {"total": 1, "overview": ""}


def test_weekly_endpoint_overview_flag(client, monkeypatch):
    monkeypatch.setattr(
        routes,
        "build_weekly_report",
        lambda overview=False: {"total": 1, "overview": "x" if overview else ""},
    )
    assert client.get("/weekly?overview=true").json()["overview"] == "x"


def test_run_weekly_starts_background_job(client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "is_busy", lambda: False)
    monkeypatch.setattr(routes, "safe_run", lambda job, name: calls.append(name))
    response = client.post("/run-weekly")
    assert response.json() == {"status": "started", "job": "Weekly report"}
    assert calls == ["Weekly report"]

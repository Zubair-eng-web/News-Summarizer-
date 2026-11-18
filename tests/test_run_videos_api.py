import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_run_videos_starts_background_job(client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "is_busy", lambda: False)
    monkeypatch.setattr(routes, "safe_run", lambda job, name: calls.append(name))
    response = client.post("/run-videos")
    assert response.json() == {"status": "started", "job": "Videos"}
    assert calls == ["Videos"]

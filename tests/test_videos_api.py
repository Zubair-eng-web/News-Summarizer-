import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_videos_endpoint(client, monkeypatch):
    monkeypatch.setattr(routes, "get_recent_videos", lambda limit: [{"video_id": "x", "title": "T"}])
    response = client.get("/videos?limit=3")
    assert response.status_code == 200
    assert response.json() == {"count": 1, "videos": [{"video_id": "x", "title": "T"}]}


def test_videos_limit_validation(client):
    assert client.get("/videos?limit=0").status_code == 422

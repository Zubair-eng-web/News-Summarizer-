import httpx
from fastapi.testclient import TestClient

from dashboard import api_client


def test_dashboard_research_posts_topic(monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, request.content))
        return httpx.Response(200, json={"report": "ok", "sources": [], "coverage": []})

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    assert api_client.research("egypt trains")["report"] == "ok"
    assert seen[0][:2] == ("POST", "/research")
    assert b"egypt trains" in seen[0][2]


def test_research_route_is_registered():
    from app.main import app

    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/research" in paths
    assert "post" in paths["/research"]
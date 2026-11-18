import json

import httpx
import pytest

from dashboard import api_client
from dashboard.api_client import ApiError


def use_handler(monkeypatch, handler):
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))


def test_get_stories_sends_filters(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"count": 0, "stories": []})

    use_handler(monkeypatch, handler)
    data = api_client.get_stories(limit=5, priority="High", hours=24)
    assert data == {"count": 0, "stories": []}
    assert seen[0].url.path == "/stories"
    params = seen[0].url.params
    assert params["limit"] == "5"
    assert params["priority"] == "High"
    assert params["hours"] == "24"


def test_get_stories_without_filters_sends_only_limit(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"count": 0, "stories": []})

    use_handler(monkeypatch, handler)
    api_client.get_stories(limit=7)
    params = seen[0].url.params
    assert params["limit"] == "7"
    assert "priority" not in params
    assert "hours" not in params


def test_ask_posts_question(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"answer": "Jawab [1]", "sources": []})

    use_handler(monkeypatch, handler)
    result = api_client.ask("Bank ne kya kiya?")
    assert result["answer"] == "Jawab [1]"
    assert seen[0].method == "POST"
    assert seen[0].url.path == "/chat"
    assert json.loads(seen[0].content) == {"question": "Bank ne kya kiya?"}


def test_api_down_gives_helpful_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    use_handler(monkeypatch, handler)
    with pytest.raises(ApiError, match="uvicorn"):
        api_client.health()


def test_http_error_uses_api_detail_message(monkeypatch):
    def handler(request):
        return httpx.Response(409, json={"detail": "Dusra job abhi chal raha hai"})

    use_handler(monkeypatch, handler)
    with pytest.raises(ApiError, match="Dusra job"):
        api_client.run_digest()


def test_http_error_without_json_falls_back(monkeypatch):
    def handler(request):
        return httpx.Response(500, text="oops")

    use_handler(monkeypatch, handler)
    with pytest.raises(ApiError, match="500"):
        api_client.get_stats()


def test_run_digest_and_alerts_use_post(monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path))
        return httpx.Response(200, json={"status": "started"})

    use_handler(monkeypatch, handler)
    assert api_client.run_digest() == {"status": "started"}
    assert api_client.run_alerts() == {"status": "started"}
    assert seen == [("POST", "/run-digest"), ("POST", "/run-alerts")]


def test_health_and_stats(monkeypatch):
    def handler(request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(200, json={"articles": 3, "stories": 2})

    use_handler(monkeypatch, handler)
    assert api_client.health()["status"] == "ok"
    assert api_client.get_stats()["articles"] == 3

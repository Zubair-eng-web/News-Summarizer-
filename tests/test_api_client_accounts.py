import httpx
import pytest

from dashboard import api_client


def use_handler(monkeypatch, handler):
    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))


def test_login_sends_credentials(monkeypatch):
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"access_token": "tok", "user": {"email": "a@b.co"}})

    use_handler(monkeypatch, handler)
    assert api_client.login("a@b.co", "password123")["access_token"] == "tok"
    assert seen["path"] == "/auth/login"
    assert "a@b.co" in seen["body"]


def test_my_feed_sends_bearer_token(monkeypatch):
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        seen["limit"] = request.url.params.get("limit")
        return httpx.Response(200, json={"interests": [], "count": 0, "stories": []})

    use_handler(monkeypatch, handler)
    assert api_client.my_feed("tok123", limit=5)["count"] == 0
    assert seen["auth"] == "Bearer tok123"
    assert seen["limit"] == "5"


def test_save_my_interests_uses_put(monkeypatch):
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"interests": ["ai"]})

    use_handler(monkeypatch, handler)
    assert api_client.save_my_interests("tok", "ai")["interests"] == ["ai"]
    assert seen == {"method": "PUT", "auth": "Bearer tok"}


def test_error_detail_is_shown(monkeypatch):
    use_handler(monkeypatch, lambda request: httpx.Response(401, json={"detail": "Login chahiye"}))
    with pytest.raises(api_client.ApiError, match="Login chahiye"):
        api_client.my_feed("bad")
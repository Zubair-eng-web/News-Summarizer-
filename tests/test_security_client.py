import httpx

from app.core.config import settings
from dashboard import api_client


def run_with(monkeypatch, key):
    seen = []

    def handler(request):
        seen.append(request.headers.get("x-api-key"))
        return httpx.Response(200, json={"ok": True})

    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(settings, "api_key", key)
    api_client.get_stats()
    return seen


def test_client_sends_api_key_when_configured(monkeypatch):
    assert run_with(monkeypatch, "abc") == ["abc"]


def test_client_sends_no_header_without_key(monkeypatch):
    assert run_with(monkeypatch, "") == [None]

import httpx

from dashboard import api_client


def _capture(monkeypatch, forwarded):
    seen = {}

    def handler(request):
        seen["xff"] = request.headers.get("x-forwarded-for")
        return httpx.Response(200, json={"status": "ok"})

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(api_client, "_forward_headers", lambda: forwarded)
    return seen


def test_visitor_ip_is_forwarded(monkeypatch):
    seen = _capture(monkeypatch, {"X-Forwarded-For": "1.2.3.4"})
    api_client.health()
    assert seen["xff"] == "1.2.3.4"


def test_no_header_when_ip_unknown(monkeypatch):
    seen = _capture(monkeypatch, {})
    api_client.health()
    assert seen["xff"] is None


def test_forward_headers_never_raises_outside_streamlit():
    assert isinstance(api_client._forward_headers(), dict)
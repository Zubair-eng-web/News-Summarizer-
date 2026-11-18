import httpx

from dashboard import api_client


def test_get_and_save_delivery(monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, request.headers.get("authorization")))
        return httpx.Response(200, json={"email": "a@b.co", "digest_enabled": True})

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    assert api_client.get_delivery("tok")["digest_enabled"] is True
    assert api_client.save_delivery("tok", True)["email"] == "a@b.co"
    assert seen == [
        ("GET", "/me/delivery", "Bearer tok"),
        ("PUT", "/me/delivery", "Bearer tok"),
    ]
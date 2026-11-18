import httpx

from dashboard import api_client


def test_sources_calls(monkeypatch):
    seen = []

    def handler(request):
        seen.append(
            (request.method, request.url.path, request.headers.get("authorization"), request.content)
        )
        return httpx.Response(200, json={"limit": 8, "sources": [], "deleted": 5})

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    assert api_client.my_sources("tok")["limit"] == 8
    api_client.add_my_source("tok", "rss", "https://example.com/rss", "Blog")
    assert api_client.delete_my_source("tok", 5)["deleted"] == 5
    assert [(m, p, a) for m, p, a, _ in seen] == [
        ("GET", "/me/sources", "Bearer tok"),
        ("POST", "/me/sources", "Bearer tok"),
        ("DELETE", "/me/sources/5", "Bearer tok"),
    ]
    assert b"example.com" in seen[1][3]
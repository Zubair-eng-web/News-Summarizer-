import httpx

from dashboard import api_client


def test_interests_get_and_save(monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, request.content))
        return httpx.Response(200, json={"interests": ["cricket"]})

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))

    assert api_client.get_interests() == {"interests": ["cricket"]}
    assert api_client.save_interests("cricket") == {"interests": ["cricket"]}
    assert seen[0][:2] == ("GET", "/interests")
    assert seen[1][:2] == ("PUT", "/interests")
    assert b"cricket" in seen[1][2]
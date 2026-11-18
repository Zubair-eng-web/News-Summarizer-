from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents import web_check as wc
from app.agents.research import ResearchError
from app.api import web_routes
from app.api.demo import is_blocked


def make_response(text, uris=()):
    chunks = [SimpleNamespace(web=SimpleNamespace(uri=u, title=f"T {u}")) for u in uris]
    meta = SimpleNamespace(grounding_chunks=chunks)
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(grounding_metadata=meta)])


class FakeClient:
    def __init__(self, response):
        self.models = self
        self.response = response
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_answer_with_unique_sources_and_search_tool():
    client = FakeClient(make_response("Claim looks supported.", ["http://a", "http://b", "http://a"]))
    result = wc.web_check("some claim", client)
    assert result["grounded"] is True
    assert [s["link"] for s in result["sources"]] == ["http://a", "http://b"]
    assert client.kwargs["config"].tools


def test_no_sources_means_no_answer():
    result = wc.web_check("claim", FakeClient(make_response("Made up answer", [])))
    assert result["answer"] == wc.NO_WEB
    assert result["sources"] == [] and result["grounded"] is False


def test_empty_text_means_no_answer():
    result = wc.web_check("claim", FakeClient(make_response("  ", ["http://a"])))
    assert result["answer"] == wc.NO_WEB


def test_sources_are_limited():
    uris = [f"http://s{i}" for i in range(10)]
    assert len(wc.extract_sources(make_response("x", uris))) == wc.MAX_SOURCES


def route_client():
    app = FastAPI()
    app.include_router(web_routes.router)
    return TestClient(app)


def test_route_returns_result(monkeypatch):
    monkeypatch.setattr(web_routes, "web_check", lambda text: {"answer": text, "sources": []})
    r = route_client().post("/research/web", json={"text": "abc def"})
    assert r.status_code == 200 and r.json()["answer"] == "abc def"


def test_route_error_codes(monkeypatch):
    def no_key(text):
        raise ValueError("GEMINI_API_KEY missing")

    def gemini_down(text):
        raise ResearchError("down")

    client = route_client()
    monkeypatch.setattr(web_routes, "web_check", no_key)
    assert client.post("/research/web", json={"text": "abc def"}).status_code == 503
    monkeypatch.setattr(web_routes, "web_check", gemini_down)
    assert client.post("/research/web", json={"text": "abc def"}).status_code == 502
    assert client.post("/research/web", json={"text": "ab"}).status_code == 422


def test_route_rate_limited(monkeypatch):
    monkeypatch.setattr(web_routes.ratelimit, "hit", lambda *a, **k: 5)
    r = route_client().post("/research/web", json={"text": "abc def"})
    assert r.status_code == 429 and r.headers["retry-after"] == "6"


def test_web_check_is_allowed_in_demo_mode():
    assert not is_blocked("POST", "/research/web")
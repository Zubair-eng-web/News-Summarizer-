import httpx
import streamlit as st
from fastapi import FastAPI
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app.agents import related as related_agent
from app.agents.research import Doc
from app.api import related as related_api
from dashboard import api_client
from dashboard.oracle import logic

DOCS = [
    Doc("Flood hits Sindh", "Flood hits Sindh. Heavy rain floods villages",
        [("Dawn", "https://d.example/1")], "story"),
    Doc("Cricket squad named", "Cricket squad named. Fifteen players",
        [("BBC", "https://b.example/1")], "article"),
]
VIDEOS = [
    {"title": "Flood relief explained", "summary": "Floods in Sindh", "channel": "DW",
     "link": "https://y.example/1", "video_id": "abcdefghijk"},
    {"title": "Cooking show", "summary": "pasta", "channel": "X",
     "link": "https://y.example/2", "video_id": "bbbbbbbbbbb"},
]


def test_related_content():
    out = related_agent.related_content("flood sindh", docs=DOCS, videos=VIDEOS)
    assert out["articles"][0]["title"] == "Flood hits Sindh"
    assert out["articles"][0]["sources"][0]["link"] == "https://d.example/1"
    assert [v["video_id"] for v in out["videos"]] == ["abcdefghijk"]
    assert related_agent.related_content("", docs=DOCS, videos=VIDEOS)["articles"] == []
    assert related_agent.related_content("zzzz", docs=DOCS, videos=VIDEOS)["videos"] == []


def test_related_endpoint(monkeypatch):
    monkeypatch.setattr(related_agent, "load_documents", lambda: DOCS)
    monkeypatch.setattr(related_agent, "get_recent_videos", lambda limit=100: VIDEOS)
    app = FastAPI()
    app.include_router(related_api.router)
    c = TestClient(app)
    body = c.get("/related", params={"q": "flood sindh"}).json()
    assert body["articles"] and body["videos"]
    assert c.get("/related", params={"q": "a"}).status_code == 422


def test_split_report():
    main, nc = logic.split_report("Overview\n- finding [1]\n\n4. Not covered: reaction of X")
    assert main.endswith("finding [1]") and nc.startswith("4. Not covered")
    main, nc = logic.split_report("Overview\n\n**Not covered**\n- more")
    assert nc.startswith("**Not covered**")
    assert logic.split_report("Only text") == ("Only text", "")
    assert logic.split_report("") == ("", "")


def test_markdown_exports():
    result = {
        "topic": "Floods", "report": "Body [1]",
        "coverage": [{"question": "q1", "hits": 2, "followup": "q1b"}],
        "sources": [{"n": 1, "title": "Flood", "sources": [{"source": "Dawn", "link": "https://d"}]}],
        "web": {"answer": "Web says", "sources": [{"title": "T", "link": "https://w"}]},
    }
    md = logic.research_markdown(result)
    assert "# Research: Floods" in md and "follow-up search: q1b" in md
    assert "Dawn https://d" in md and "## Web check" in md
    chat = logic.chat_markdown([
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Answer",
         "sources": [{"n": 1, "title": "Flood", "sources": [{"source": "Dawn", "link": "https://d"}]}]},
    ])
    assert "**You:** Hi" in chat and "**ORACLE:** Answer" in chat and "https://d" in chat


def test_api_client_related(monkeypatch):
    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(
        lambda r: httpx.Response(200, json={"articles": [], "videos": []})))
    assert api_client.related("flood") == {"articles": [], "videos": []}


STORY = {"id": 1, "title": "Flood hits Sindh", "summary": "Rain.", "priority": "Critical",
         "sentiment": "negative", "credibility": "Single source", "category": "Disaster",
         "created_at": "2026-11-18T09:00:00",
         "sources": [{"source": "Dawn", "link": "https://d.example/1"}], "claims": []}
CITED = {"n": 1, "title": "Flood", "sources": [{"source": "Dawn", "link": "https://d.example/1"}]}


def _install(monkeypatch, routes):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        body = routes.get((request.method, request.url.path))
        if body is None:
            return httpx.Response(404, json={"detail": "nf"})
        return httpx.Response(200, json=body)

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    st.cache_data.clear()
    return calls


def _chat_page():
    return AppTest.from_string(
        "from dashboard.oracle import research\nresearch.chat()", default_timeout=30)


def test_chat_with_related(monkeypatch):
    routes = {
        ("GET", "/stories"): {"count": 1, "stories": [STORY]},
        ("POST", "/chat"): {"answer": "Floods hit Sindh [1].", "query": "flood sindh",
                            "sources": [CITED]},
        ("GET", "/related"): {
            "articles": [
                {"title": "Same", "sources": [{"source": "Dawn", "link": "https://d.example/1"}]},
                {"title": "Other", "sources": [{"source": "BBC", "link": "https://b.example/2"}]},
            ],
            "videos": [{"title": "Vid", "channel": "DW", "link": "https://y.example/1"}],
        },
    }
    calls = _install(monkeypatch, routes)
    at = _chat_page().run()
    at.chat_input[0].set_value("Flood?").run()
    assert not at.exception
    assert "/related" in calls


def test_chat_refusal_skips_related(monkeypatch):
    routes = {
        ("GET", "/stories"): {"count": 0, "stories": []},
        ("POST", "/chat"): {"answer": "Nothing found.", "query": "x", "sources": []},
    }
    calls = _install(monkeypatch, routes)
    at = _chat_page().run()
    at.chat_input[0].set_value("Unknown topic?").run()
    assert not at.exception
    assert "/related" not in calls
    assert any("does not support" in i.value for i in at.info)


def test_chat_survives_related_error(monkeypatch):
    routes = {
        ("GET", "/stories"): {"count": 0, "stories": []},
        ("POST", "/chat"): {"answer": "Answer [1].", "query": "q", "sources": [CITED]},
    }
    _install(monkeypatch, routes)
    at = _chat_page().run()
    at.chat_input[0].set_value("Flood?").run()
    assert not at.exception


def test_research_shows_not_covered(monkeypatch):
    routes = {("POST", "/research"): {
        "report": "Overview [1]\n\n4. Not covered: the reaction of X",
        "coverage": [{"question": "q1", "hits": 0, "followup": "q1b"}], "sources": []}}
    _install(monkeypatch, routes)
    at = AppTest.from_string(
        "from dashboard.oracle import research\nresearch.research()", default_timeout=30).run()
    at.text_input(key="research_topic").set_value("Floods in Sindh").run()
    at.button(key="research_go").click().run()
    assert not at.exception
    assert any("Not covered" in m.value for m in at.markdown)
    assert any("Follow-up searches" in c.value for c in at.caption)
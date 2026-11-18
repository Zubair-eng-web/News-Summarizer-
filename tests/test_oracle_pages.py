"""Run the real ORACLE pages offline with Streamlit AppTest and a fake API."""
import httpx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from dashboard import api_client

STORY = {
    "title": "Flood hits Sindh",
    "summary": "Heavy rain across the province.",
    "priority": "Critical",
    "sentiment": "negative",
    "credibility": "Confirmed by 2 sources",
    "created_at": "2026-11-18T09:00:00",
    "sources": [{"source": "Dawn", "link": "https://d.example/1"},
                {"source": "BBC World", "link": "https://b.example/1"}],
    "claims": [{"claim": "Rate unchanged", "status": "disputed",
                "supported_by": ["Dawn"], "contradicted_by": ["BBC World"]}],
    "matched_interests": ["flood"],
}
VIDEO = {
    "title": "AI weekly", "link": "https://y.example/v", "channel": "TechChannel",
    "published": "2026-11-17T10:00:00", "summary": "A summary.", "key_points": ["Point one"],
    "takeaway": "Be careful.", "has_transcript": True,
}
ROUTES = {
    ("GET", "/health"): {"status": "ok", "debug": True},
    ("GET", "/stats"): {"articles": 9, "stories": 3, "alerts_sent": 2,
                        "stories_by_priority": {"Critical": 1, "High": 1, "Medium": 1, "Low": 0}},
    ("GET", "/stories"): {"count": 1, "stories": [STORY]},
    ("GET", "/videos"): {"count": 1, "videos": [VIDEO]},
    ("GET", "/interests"): {"interests": ["ai"]},
    ("PUT", "/interests"): {"interests": ["ai", "cricket"]},
    ("POST", "/chat"): {"answer": "Floods hit Sindh.", "sources": [
        {"n": 1, "title": "Flood", "sources": [{"source": "Dawn", "link": "https://d.example/1"}]}]},
    ("POST", "/research"): {"report": "Report text", "coverage": [{"question": "Q1", "hits": 2}],
                            "sources": [], "web": {"answer": "Web answer",
                            "sources": [{"title": "T", "link": "https://w.example"}]}},
    ("POST", "/research/web"): {"answer": "Checked", "sources": [
        {"title": "T", "link": "https://w.example"}]},
    ("GET", "/me/feed"): {"interests": ["flood"], "scope": "all", "count": 1, "stories": [STORY]},
    ("GET", "/me/delivery"): {"email": "a@b.com", "digest_enabled": True,
                              "telegram_chat_id": "", "digest_hour": None},
    ("GET", "/me/sources"): {"limit": 8, "sources": [
        {"id": 1, "name": "My feed", "kind": "rss", "url": "https://x.example/rss"}]},
}


def _handler(down: bool = False):
    def handler(request: httpx.Request) -> httpx.Response:
        if down:
            raise httpx.ConnectError("down")
        body = ROUTES.get((request.method, request.url.path))
        if body is None:
            return httpx.Response(404, json={"detail": "not found"})
        return httpx.Response(200, json=body)
    return handler


@pytest.fixture(autouse=True)
def fake_api(monkeypatch):
    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(_handler()))
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def run(module: str, func: str, logged_in: bool = False) -> AppTest:
    at = AppTest.from_string(
        f"from dashboard.oracle import {module}\n{module}.{func}()", default_timeout=30
    )
    if logged_in:
        at.session_state["token"] = "t"
        at.session_state["user_email"] = "a@b.com"
    at.run()
    return at


PAGES = [
    ("overview", "render"), ("feed", "news_feed"), ("feed", "youtube"),
    ("research", "research"), ("research", "chat"), ("misc", "analytics"),
    ("misc", "alerts"), ("misc", "sources"), ("misc", "delivery"),
    ("misc", "system"), ("misc", "account_page"), ("sidebar", "render"),
]


@pytest.mark.parametrize("module,func", PAGES)
def test_page_renders_logged_out(module, func):
    assert not run(module, func).exception


@pytest.mark.parametrize("module,func", [("feed", "my_feed"), ("misc", "sources"),
                                         ("misc", "delivery"), ("misc", "account_page")])
def test_page_renders_logged_in(module, func):
    assert not run(module, func, logged_in=True).exception


def test_pages_survive_api_down(monkeypatch):
    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(_handler(down=True)))
    for module, func in [("overview", "render"), ("feed", "news_feed"), ("misc", "analytics"),
                         ("misc", "alerts"), ("misc", "system")]:
        st.cache_data.clear()
        at = run(module, func)
        assert not at.exception
        assert at.error


def test_research_flow():
    at = run("research", "research")
    at.text_input(key="research_topic").set_value("Floods in Sindh").run()
    at.button(key="research_go").click().run()
    assert not at.exception
    assert any("Sub-questions" in c.value for c in at.caption)


def test_web_check_flow():
    at = run("research", "research")
    at.text_input(key="web_text").set_value("Flood claim").run()
    at.button(key="web_go").click().run()
    assert not at.exception


def test_chat_flow():
    at = run("research", "chat")
    at.chat_input[0].set_value("Aaj ki badi khabar?").run()
    assert not at.exception
    assert len(at.chat_message) >= 2
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest
import streamlit as st
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from app.api import bookmarks as bookmarks_api
from app.api.auth import get_current_user
from app.collectors.rss import extract_image, image_extra
from app.core import bookmarks
from app.core.category import CATEGORIES, categorize
from app.core.database import Base
from app.core.models import StoryDB
from app.core.storage import _story_to_dict
from app.pipeline import pick_image
from dashboard import api_client
from dashboard.oracle import logic


def test_extract_image_sources():
    assert extract_image({"media_thumbnail": [{"url": "https://i.example/a.jpg"}]}) == (
        "https://i.example/a.jpg"
    )
    media = {"media_content": [{"url": "https://v.example/v.mp4", "medium": "video"},
                               {"url": "https://i.example/b.jpg", "medium": "image"}]}
    assert extract_image(media) == "https://i.example/b.jpg"
    enc = {"enclosures": [{"href": "https://i.example/c.png", "type": "image/png"}]}
    assert extract_image(enc) == "https://i.example/c.png"
    link = {"links": [{"href": "https://i.example/d.jpg", "type": "image/jpeg"}]}
    assert extract_image(link) == "https://i.example/d.jpg"
    assert extract_image({"media_thumbnail": [{"url": "javascript:alert(1)"}]}) == ""
    assert extract_image({}) == ""
    assert image_extra({}) == {}
    assert image_extra({"media_thumbnail": [{"url": "https://i.example/a.jpg"}]}) == {
        "image": "https://i.example/a.jpg"
    }


def test_pick_image():
    group = [SimpleNamespace(extra={}), SimpleNamespace(extra={"image": "https://i.example/x.jpg"})]
    assert pick_image(group) == "https://i.example/x.jpg"
    assert pick_image([SimpleNamespace(extra={})]) == ""


def test_categorize():
    assert categorize("Major earthquake drill held across coastal cities") == "Disaster"
    assert categorize("Cricket team announces squad for upcoming series") == "Sports"
    assert categorize("Central bank holds interest rate steady",
                      "Inflation is easing slowly.") == "Business"
    assert categorize("Local food festival returns this weekend") == "Other"
    assert "Other" in CATEGORIES


def test_story_dict_has_image_and_category():
    row = StoryDB(id=1, title="Earthquake drill", summary="Cities", sources_json="[]",
                  created_at=datetime(2026, 11, 18), image_url="https://i.example/a.jpg")
    d = _story_to_dict(row)
    assert d["image_url"] == "https://i.example/a.jpg"
    assert d["category"] == "Disaster"


def test_filter_category_and_days():
    now = datetime(2026, 11, 18, 12)
    old = {"title": "Old", "category": "Sports", "created_at": "2026-11-10T10:00:00", "sources": []}
    new = {"title": "New", "category": "Sports", "created_at": "2026-11-18T10:00:00", "sources": []}
    biz = {"title": "Biz", "category": "Business", "created_at": "2026-11-18T09:00:00",
           "sources": []}
    out = logic.filter_stories([old, new, biz], category="Sports", days=7, now=now)
    assert [s["title"] for s in out] == ["New"]
    assert len(logic.filter_stories([old, new, biz], now=now)) == 3


def test_csv_and_thumbnail():
    csv_text = logic.stories_csv([{"title": "=HYPERLINK(1)", "summary": "x",
                                  "sources": [{"source": "Dawn"}], "priority": "High"}])
    assert "'=HYPERLINK(1)" in csv_text and "Dawn" in csv_text
    assert logic.youtube_thumbnail("dQw4w9WgXcQ") == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    assert logic.youtube_thumbnail("bad id") == ""
    assert logic.youtube_thumbnail(None) == ""


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(bookmarks, "SessionLocal", session_factory)
    monkeypatch.setattr(bookmarks, "init_db", lambda: None)
    with session_factory() as s:
        s.add(StoryDB(title="Story A", summary="s",
                      sources_json='[["Dawn", "https://d.example/1"]]'))
        s.commit()
    return session_factory


def test_bookmark_core(db):
    assert bookmarks.add_bookmark(7, 1) is True
    assert bookmarks.add_bookmark(7, 1) is False
    assert [s["title"] for s in bookmarks.list_bookmarked_stories(7)] == ["Story A"]
    assert bookmarks.list_bookmarked_stories(8) == []
    with pytest.raises(bookmarks.StoryNotFoundError):
        bookmarks.add_bookmark(7, 999)
    assert bookmarks.remove_bookmark(7, 1) is True
    assert bookmarks.remove_bookmark(7, 1) is False


def test_bookmark_limit(db, monkeypatch):
    monkeypatch.setattr(bookmarks, "MAX_PER_USER", 0)
    with pytest.raises(bookmarks.BookmarkLimitError):
        bookmarks.add_bookmark(7, 1)


def test_bookmark_api(db):
    app = FastAPI()
    app.include_router(bookmarks_api.router)
    app.dependency_overrides[get_current_user] = lambda: {"id": 7, "email": "a@b.com",
                                                          "interests": []}
    c = TestClient(app)
    assert c.put("/me/bookmarks/1").json()["created"] is True
    assert c.put("/me/bookmarks/1").json()["created"] is False
    assert c.put("/me/bookmarks/999").status_code == 404
    body = c.get("/me/bookmarks").json()
    assert body["story_ids"] == [1] and body["count"] == 1
    assert c.delete("/me/bookmarks/1").status_code == 200
    assert c.delete("/me/bookmarks/1").status_code == 404


STORY = {
    "id": 1, "title": "Flood hits Sindh", "summary": "Rain.", "priority": "High",
    "sentiment": "negative", "credibility": "Single source", "category": "Disaster",
    "image_url": "https://i.example/a.jpg", "created_at": "2026-11-18T09:00:00",
    "sources": [{"source": "Dawn", "link": "https://d.example/1"}], "claims": [],
}
VIDEO = {"video_id": "dQw4w9WgXcQ", "title": "AI weekly", "link": "https://y.example/v",
         "channel": "Tech", "published": "2026-11-17T10:00:00", "summary": "S",
         "key_points": ["P"], "takeaway": "T", "has_transcript": True}


def _install(monkeypatch, saved_ids):
    routes = {
        ("GET", "/stories"): {"count": 1, "stories": [STORY]},
        ("GET", "/videos"): {"count": 1, "videos": [VIDEO]},
        ("GET", "/me/bookmarks"): {"count": len(saved_ids), "limit": 200, "story_ids": saved_ids,
                                   "stories": [STORY] if saved_ids else []},
        ("PUT", "/me/bookmarks/1"): {"story_id": 1, "saved": True, "created": True},
        ("DELETE", "/me/bookmarks/1"): {"story_id": 1, "saved": False},
    }

    def handler(request):
        body = routes.get((request.method, request.url.path))
        return httpx.Response(200, json=body) if body is not None else httpx.Response(
            404, json={"detail": "nf"})

    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    st.cache_data.clear()


def _page(code, logged_in):
    at = AppTest.from_string(code, default_timeout=30)
    if logged_in:
        at.session_state["token"] = "t"
        at.session_state["user_email"] = "a@b.com"
    at.run()
    return at


def test_news_feed_bookmark_flow(monkeypatch):
    _install(monkeypatch, [])
    at = _page("from dashboard.oracle import feed\nfeed.news_feed()", True)
    assert not at.exception
    at.button(key="bm_nf_1").click().run()
    assert not at.exception


def test_news_feed_logged_out_and_filters(monkeypatch):
    _install(monkeypatch, [])
    at = _page("from dashboard.oracle import feed\nfeed.news_feed()", False)
    assert not at.exception
    at.selectbox(key="nf_cat").select("Sports").run()
    assert not at.exception


def test_saved_page(monkeypatch):
    _install(monkeypatch, [1])
    assert not _page("from dashboard.oracle import feed\nfeed.saved()", True).exception
    assert not _page("from dashboard.oracle import feed\nfeed.saved()", False).exception


def test_youtube_views(monkeypatch):
    _install(monkeypatch, [])
    at = _page("from dashboard.oracle import feed\nfeed.youtube()", False)
    assert not at.exception
    at.selectbox(key="yt_view").select("By channel").run()
    assert not at.exception
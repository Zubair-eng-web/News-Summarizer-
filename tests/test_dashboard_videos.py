from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

from dashboard import api_client, utils

APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")

STORIES = {
    "count": 1,
    "stories": [
        {
            "id": 1,
            "title": "Big quake",
            "summary": "Summary one.",
            "priority": "Critical",
            "sentiment": "negative",
            "credibility": "Single source",
            "sources": [{"source": "BBC", "link": "http://bbc/1"}],
            "created_at": "2026-11-05T14:30:00",
        }
    ],
}
STATS = {
    "articles": 5,
    "stories": 1,
    "alerts_sent": 0,
    "stories_by_priority": {"Critical": 1, "High": 0, "Medium": 0, "Low": 0},
}
VIDEOS = {
    "count": 1,
    "videos": [
        {
            "video_id": "v1",
            "title": "Big video",
            "link": "https://youtu.be/v1",
            "channel": "BBC News",
            "published": "2026-11-05T10:00:00",
            "summary": "Video summary.",
            "key_points": ["Point A"],
            "takeaway": "Main takeaway.",
            "has_transcript": True,
        }
    ],
}


def fake_api(monkeypatch, videos=VIDEOS):
    monkeypatch.setattr(api_client, "health", lambda: {"status": "ok"})
    monkeypatch.setattr(api_client, "get_stories", lambda limit=20, priority=None, hours=None: STORIES)
    monkeypatch.setattr(api_client, "get_stats", lambda: STATS)
    monkeypatch.setattr(api_client, "ask", lambda question: {"answer": "x", "sources": []})
    if callable(videos):
        monkeypatch.setattr(api_client, "get_videos", videos)
    else:
        monkeypatch.setattr(api_client, "get_videos", lambda limit=10: videos)


def test_client_video_endpoints(monkeypatch):
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, dict(request.url.params)))
        return httpx.Response(200, json={"ok": True})

    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.setattr(api_client, "_transport", httpx.MockTransport(handler))
    api_client.get_videos(limit=7)
    api_client.run_videos()
    assert seen == [("GET", "/videos", {"limit": "7"}), ("POST", "/run-videos", {})]


def test_link_markdown_is_safe():
    assert utils.link_markdown("Big [news] $1", "http://x.com/a(1)") == "[Big (news) \\$1](http://x.com/a%281%29)"
    assert utils.link_markdown("Title", "javascript:alert(1)") == "Title"


def test_dashboard_shows_video_card(monkeypatch):
    fake_api(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert any("Big video" in m.value for m in at.markdown)
    assert any("Main takeaway" in i.value for i in at.info)


def test_dashboard_shows_message_when_no_videos(monkeypatch):
    fake_api(monkeypatch, videos={"count": 0, "videos": []})
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert any("video summary" in i.value for i in at.info)


def test_dashboard_shows_error_when_videos_api_fails(monkeypatch):
    def broken(limit=10):
        raise api_client.ApiError("Videos band hain")

    fake_api(monkeypatch, videos=broken)
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert any("Videos band hain" in e.value for e in at.error)

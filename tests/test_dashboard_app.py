from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard import api_client

APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")

STORIES = {
    "count": 2,
    "stories": [
        {
            "id": 1,
            "title": "Big quake",
            "summary": "Summary one costs $1M.",
            "priority": "Critical",
            "sentiment": "negative",
            "credibility": "Confirmed by 2 sources",
            "sources": [
                {"source": "BBC", "link": "http://bbc/1"},
                {"source": "Dawn", "link": "http://dawn/1"},
            ],
            "created_at": "2026-11-05T14:30:00",
        },
        {
            "id": 2,
            "title": "Football result",
            "summary": "Summary two.",
            "priority": "Low",
            "sentiment": "positive",
            "credibility": "Single source",
            "sources": [{"source": "Dawn", "link": "http://dawn/2"}],
            "created_at": "2026-11-05T14:30:00",
        },
    ],
}
STATS = {
    "articles": 15,
    "stories": 2,
    "alerts_sent": 1,
    "stories_by_priority": {"Critical": 1, "High": 0, "Medium": 0, "Low": 1},
}
ANSWER = {
    "answer": "Jawab [1]",
    "sources": [
        {"n": 1, "title": "Big quake", "score": 0.9, "sources": [{"source": "BBC", "link": "http://bbc/1"}]}
    ],
}


def fake_api(monkeypatch):
    monkeypatch.setattr(api_client, "health", lambda: {"status": "ok"})
    monkeypatch.setattr(
        api_client, "get_stories", lambda limit=20, priority=None, hours=None: STORIES
    )
    monkeypatch.setattr(api_client, "get_stats", lambda: STATS)
    monkeypatch.setattr(api_client, "ask", lambda question: ANSWER)
    monkeypatch.setattr(api_client, "get_videos", lambda limit=10: {"count": 0, "videos": []})


def test_dashboard_renders_with_data(monkeypatch):
    fake_api(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert at.title[0].value == "AI Briefing Agent"
    assert len(at.metric) == 3


def test_dashboard_shows_error_when_api_is_down(monkeypatch):
    def down():
        raise api_client.ApiError("API band hai")

    monkeypatch.setattr(api_client, "health", down)
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert len(at.error) == 1
    assert "band" in at.error[0].value


def test_chat_flow_shows_question_and_answer(monkeypatch):
    fake_api(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=20).run()
    at.chat_input[0].set_value("Bank ne kya kiya?").run()
    assert not at.exception
    assert len(at.chat_message) == 2

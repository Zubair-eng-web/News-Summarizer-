from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.core.config import settings
from dashboard import api_client

APP = str(Path(__file__).resolve().parent.parent / "dashboard" / "app.py")

STATS = {
    "articles": 5,
    "stories": 0,
    "alerts_sent": 0,
    "stories_by_priority": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
}


def fake_api(monkeypatch):
    monkeypatch.setattr(api_client, "health", lambda: {"status": "ok"})
    monkeypatch.setattr(
        api_client, "get_stories", lambda limit=20, priority=None, hours=None: {"count": 0, "stories": []}
    )
    monkeypatch.setattr(api_client, "get_stats", lambda: STATS)
    monkeypatch.setattr(api_client, "get_videos", lambda limit=10: {"count": 0, "videos": []})
    monkeypatch.setattr(api_client, "ask", lambda question: {"answer": "x", "sources": []})


def test_dashboard_is_locked_until_password_is_entered(monkeypatch):
    fake_api(monkeypatch)
    monkeypatch.setattr(settings, "dashboard_password", "pw-123")
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    assert len(at.text_input) == 1
    assert len(at.metric) == 0  # dashboard ka asal hissa chhupa hua hai


def test_wrong_password_shows_error(monkeypatch):
    fake_api(monkeypatch)
    monkeypatch.setattr(settings, "dashboard_password", "pw-123")
    at = AppTest.from_file(APP, default_timeout=20).run()
    at.text_input[0].set_value("wrong").run()
    assert any("Ghalat" in e.value for e in at.error)
    assert len(at.metric) == 0


def test_correct_password_opens_dashboard(monkeypatch):
    fake_api(monkeypatch)
    monkeypatch.setattr(settings, "dashboard_password", "pw-123")
    at = AppTest.from_file(APP, default_timeout=20).run()
    at.text_input[0].set_value("pw-123").run()
    assert not at.exception
    assert len(at.metric) == 3

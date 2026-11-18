import pytest

from app.agents.email_agent import build_html, build_message, send_email
from app.core.config import settings
from app.pipeline import Story

STORIES = [
    Story(title="Rates <b>up</b>", summary="Summary one.", sources=[("BBC", "http://bbc.com/a")]),
    Story(title="AI chip", summary="Summary two.", sources=[("TechCrunch", "http://tc.com/b")]),
]


class FakeSMTP:
    sent = []
    logged_in = None

    def __init__(self, host, port, **kwargs):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, user, password):
        FakeSMTP.logged_in = (user, password)

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def test_html_contains_stories_and_links():
    html = build_html(STORIES, "05 November 2026")
    assert "Summary one." in html
    assert 'href="http://bbc.com/a"' in html
    assert "05 November 2026" in html


def test_html_is_escaped():
    html = build_html(STORIES, "d")
    assert "<b>up</b>" not in html
    assert "&lt;b&gt;up&lt;/b&gt;" in html


def test_empty_stories_message():
    assert "nayi khabar nahi" in build_html([], "d")


def test_message_headers():
    msg = build_message(STORIES, "me@gmail.com", "you@gmail.com")
    assert msg["To"] == "you@gmail.com"
    assert "2 stories" in msg["Subject"]


def test_send_email_uses_smtp(monkeypatch):
    monkeypatch.setattr(settings, "email_sender", "me@gmail.com")
    monkeypatch.setattr(settings, "email_password", "secret")
    monkeypatch.setattr(settings, "email_receiver", "you@gmail.com")
    FakeSMTP.sent.clear()
    send_email(STORIES, smtp_class=FakeSMTP)
    assert FakeSMTP.logged_in == ("me@gmail.com", "secret")
    assert len(FakeSMTP.sent) == 1


def test_send_email_without_config_raises(monkeypatch):
    monkeypatch.setattr(settings, "email_sender", "")
    with pytest.raises(ValueError):
        send_email(STORIES, smtp_class=FakeSMTP)

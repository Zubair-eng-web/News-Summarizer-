from email.message import EmailMessage
from types import SimpleNamespace

import pytest

from app.agents.alert_agent import send_alert
from app.agents.email_agent import send_email
from app.agents.weekly_email import send_weekly_email
from app.core import mailer
from app.core.config import settings
from app.core.story import Story
from tests.test_weekly_email import REPORT

STORIES = [
    Story(title="Big quake", summary="Summary.", sources=[("BBC", "http://bbc/1")], priority="Critical")
]


def make_message(sender, receiver):
    msg = EmailMessage()
    msg["Subject"] = "Hello"
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content("plain body")
    msg.add_alternative("<p>html body</p>", subtype="html")
    return msg


class FakePost:
    def __init__(self, status=200, text="ok"):
        self.calls = []
        self.status = status
        self.text = text

    def __call__(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return SimpleNamespace(status_code=self.status, text=self.text)


class FakeSMTP:
    sent = []

    def __init__(self, host, port, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, user, password):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def use_resend(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "email_receiver", "me@gmail.com")


def test_resend_is_used_when_key_is_set(monkeypatch):
    use_resend(monkeypatch)
    post = FakePost()
    mailer.deliver(make_message, http_post=post)
    call = post.calls[0]
    assert call["url"] == "https://api.resend.com/emails"
    assert call["headers"] == {"Authorization": "Bearer re_test"}
    assert call["json"]["to"] == ["me@gmail.com"]
    assert call["json"]["from"] == settings.resend_from
    assert call["json"]["subject"] == "Hello"
    assert "html body" in call["json"]["html"]
    assert "plain body" in call["json"]["text"]


def test_resend_error_is_raised(monkeypatch):
    use_resend(monkeypatch)
    post = FakePost(status=403, text="You can only send testing emails to your own email address")
    with pytest.raises(RuntimeError, match="403"):
        mailer.deliver(make_message, http_post=post)


def test_resend_needs_a_receiver(monkeypatch):
    use_resend(monkeypatch)
    monkeypatch.setattr(settings, "email_receiver", "")
    with pytest.raises(ValueError):
        mailer.deliver(make_message, http_post=FakePost())


def test_smtp_is_used_when_smtp_class_is_given(monkeypatch):
    use_resend(monkeypatch)
    monkeypatch.setattr(settings, "email_sender", "me@gmail.com")
    monkeypatch.setattr(settings, "email_password", "secret")
    FakeSMTP.sent.clear()
    post = FakePost()
    mailer.deliver(make_message, smtp_class=FakeSMTP, http_post=post)
    assert len(FakeSMTP.sent) == 1
    assert post.calls == []


def test_missing_smtp_config_raises(monkeypatch):
    monkeypatch.setattr(settings, "email_sender", "")
    with pytest.raises(ValueError):
        mailer.deliver(make_message, smtp_class=FakeSMTP)


def test_digest_alert_and_weekly_all_use_resend(monkeypatch):
    use_resend(monkeypatch)
    post = FakePost()
    monkeypatch.setattr(mailer.httpx, "post", post)

    send_email(STORIES)
    send_alert(STORIES)
    send_weekly_email(REPORT)

    subjects = [c["json"]["subject"] for c in post.calls]
    assert len(subjects) == 3
    assert subjects[0].startswith("Daily Briefing")
    assert subjects[1].startswith("BREAKING")
    assert subjects[2].startswith("Weekly Intelligence Report")


def test_send_alert_with_no_stories_sends_nothing(monkeypatch):
    use_resend(monkeypatch)
    post = FakePost()
    monkeypatch.setattr(mailer.httpx, "post", post)
    send_alert([])
    assert post.calls == []

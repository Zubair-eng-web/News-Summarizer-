from app.agents.weekly_email import _delta, build_weekly_html, build_weekly_text, send_weekly_email
from app.core.config import settings

REPORT = {
    "start": "2026-11-01T12:00:00",
    "end": "2026-11-08T12:00:00",
    "total": 4,
    "previous_total": 2,
    "has_previous": True,
    "priority": {
        "Critical": {"count": 1, "previous": 0},
        "High": {"count": 2, "previous": 0},
        "Medium": {"count": 0, "previous": 1},
        "Low": {"count": 1, "previous": 1},
    },
    "sentiment": {
        "positive": {"count": 1, "previous": 0},
        "negative": {"count": 2, "previous": 1},
        "neutral": {"count": 1, "previous": 1},
    },
    "top_stories": [
        {
            "title": "Big <b>quake</b>",
            "summary": "Summary one.",
            "priority": "Critical",
            "sentiment": "negative",
            "credibility": "Single source",
            "sources": [{"source": "BBC", "link": "http://bbc/1"}],
        }
    ],
    "trending": [{"term": "iran war", "count": 5, "previous": 1, "status": "rising"}],
    "videos": [
        {
            "title": "Video T",
            "link": "https://youtu.be/v1",
            "channel": "BBC News",
            "summary": "Video summary.",
            "key_points": ["Point A"],
            "takeaway": "Main takeaway.",
            "has_transcript": True,
        }
    ],
    "overview": "This week was busy.",
}


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


def test_html_has_all_sections():
    html = build_weekly_html(REPORT)
    assert "Weekly Intelligence Report" in html
    assert "01 Nov - 08 Nov 2026" in html
    assert "This week was busy." in html
    assert "iran war" in html
    assert "rising" in html
    assert "Summary one." in html
    assert 'href="http://bbc/1"' in html
    assert "Video summary." in html
    assert "last week: 2" in html


def test_html_is_escaped():
    html = build_weekly_html(REPORT)
    assert "<b>quake</b>" not in html
    assert "&lt;b&gt;quake&lt;/b&gt;" in html


def test_no_previous_week_shows_note_and_no_comparison():
    report = dict(REPORT, has_previous=False, previous_total=0)
    html = build_weekly_html(report)
    assert "muqabla agle hafte" in html
    assert "Last week" not in html
    assert "rising" not in html


def test_delta_formatting():
    assert _delta(3, 1, True) == "+2"
    assert _delta(1, 3, True) == "-2"
    assert _delta(2, 2, True) == "0"
    assert _delta(2, 1, False) == ""


def test_text_version():
    text = build_weekly_text(REPORT)
    assert "Weekly Intelligence Report" in text
    assert "iran war" in text
    assert "Video T" in text
    assert "This week was busy." in text


def test_send_weekly_email_uses_smtp(monkeypatch):
    monkeypatch.setattr(settings, "email_sender", "me@gmail.com")
    monkeypatch.setattr(settings, "email_password", "secret")
    monkeypatch.setattr(settings, "email_receiver", "you@gmail.com")
    FakeSMTP.sent.clear()
    send_weekly_email(REPORT, smtp_class=FakeSMTP)
    assert len(FakeSMTP.sent) == 1
    assert "Weekly Intelligence Report" in FakeSMTP.sent[0]["Subject"]


def test_empty_week_message():
    report = dict(REPORT, total=0, top_stories=[], trending=[], videos=[], overview="")
    assert "koi story nahi" in build_weekly_html(report)

from app.agents.email_agent import build_html, build_text, send_email
from app.core.config import settings
from app.core.story import Story

STORIES = [Story(title="Rates up", summary="Summary one.", sources=[("BBC", "http://bbc.com/a")])]
VIDEOS = [
    {
        "video_id": "v1",
        "title": "Big <b>video</b>",
        "link": "https://youtu.be/v1",
        "channel": "BBC News",
        "summary": "Video summary.",
        "key_points": ["Point A", "Point B"],
        "takeaway": "Main takeaway.",
        "has_transcript": True,
    }
]


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


def test_html_has_video_section():
    html = build_html(STORIES, "d", VIDEOS)
    assert "YouTube Highlights" in html
    assert "Video summary." in html
    assert "<li>Point A</li>" in html
    assert "Main takeaway." in html
    assert 'href="https://youtu.be/v1"' in html
    assert "BBC News" in html


def test_video_content_is_escaped():
    html = build_html(STORIES, "d", VIDEOS)
    assert "<b>video</b>" not in html
    assert "&lt;b&gt;video&lt;/b&gt;" in html


def test_description_only_label():
    no_transcript = [dict(VIDEOS[0], has_transcript=False)]
    assert "description se" in build_html(STORIES, "d", no_transcript)
    assert "description se" not in build_html(STORIES, "d", VIDEOS)


def test_no_videos_means_no_section():
    assert "YouTube Highlights" not in build_html(STORIES, "d")
    assert "YouTube Highlights" not in build_html(STORIES, "d", [])


def test_text_version_has_videos():
    text = build_text(STORIES, "d", VIDEOS)
    assert "YouTube Highlights" in text
    assert "Point A" in text
    assert "https://youtu.be/v1" in text


def test_send_email_includes_videos(monkeypatch):
    monkeypatch.setattr(settings, "email_sender", "me@gmail.com")
    monkeypatch.setattr(settings, "email_password", "secret")
    monkeypatch.setattr(settings, "email_receiver", "you@gmail.com")
    FakeSMTP.sent.clear()
    send_email(STORIES, smtp_class=FakeSMTP, videos=VIDEOS)
    body = FakeSMTP.sent[0].get_body(preferencelist=("html",)).get_content()
    assert "Video summary." in body

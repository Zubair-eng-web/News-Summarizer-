import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.alert_agent import build_alert_html, build_alert_message, send_alert
from app.collectors.rss import Article
from app.core import models  # noqa: F401
from app.core import storage
from app.core.config import settings
from app.core.database import Base
from app.core.story import Story
from app.graph.briefing import build_briefing_graph


def story(title="Big quake", link="http://x.com/1", priority="Critical"):
    return Story(
        title=title,
        summary="Summary.",
        sources=[("BBC", link)],
        priority=priority,
        credibility="Single source",
    )


class FakeSMTP:
    sent = []
    logged_in = None

    def __init__(self, host, port, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, user, password):
        FakeSMTP.logged_in = (user, password)

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


class FakeModels:
    def __init__(self, priority):
        self.priority = priority

    def generate_content(self, **kwargs):
        if "news editor" in kwargs["config"].system_instruction:
            n = kwargs["contents"].count("\n") + 1
            data = [{"id": i, "priority": self.priority, "sentiment": "negative"} for i in range(1, n + 1)]
            return SimpleNamespace(text=json.dumps(data))
        return SimpleNamespace(text="Fake summary.")


class FakeClient:
    def __init__(self, priority):
        self.models = FakeModels(priority)


def make(title, source):
    return Article(title=title, link=f"http://x.com/{source}/{title}", summary="", source=source)


ARTICLES = [
    make("Bank of England raises interest rate to fight inflation", "BBC"),
    make("Bank of England lifts interest rate to fight inflation", "Dawn"),
    make("Ronaldo retires from Portugal national team", "BBC"),
]


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(storage, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(storage, "init_db", lambda: None)


def test_subject_single_story():
    msg = build_alert_message([story("Big quake")], "a@x.com", "b@x.com")
    assert msg["Subject"] == "BREAKING: Big quake"


def test_subject_multiple_stories():
    msg = build_alert_message([story("A", "http://x/1"), story("B", "http://x/2")], "a@x.com", "b@x.com")
    assert msg["Subject"] == "BREAKING: 2 critical stories"


def test_alert_html_content():
    html = build_alert_html([story("Big <quake>")])
    assert "BREAKING NEWS ALERT" in html
    assert "&lt;quake&gt;" in html
    assert 'href="http://x.com/1"' in html


def test_send_alert_uses_smtp(monkeypatch):
    monkeypatch.setattr(settings, "email_sender", "me@gmail.com")
    monkeypatch.setattr(settings, "email_password", "secret")
    monkeypatch.setattr(settings, "email_receiver", "you@gmail.com")
    FakeSMTP.sent.clear()
    send_alert([story()], smtp_class=FakeSMTP)
    assert FakeSMTP.logged_in == ("me@gmail.com", "secret")
    assert len(FakeSMTP.sent) == 1


def test_send_alert_without_config_raises(monkeypatch):
    monkeypatch.setattr(settings, "email_sender", "")
    with pytest.raises(ValueError):
        send_alert([story()], smtp_class=FakeSMTP)


def test_mark_and_filter_unalerted(temp_db):
    a, b = story("A", "http://x/a"), story("B", "http://x/b")
    assert len(storage.filter_unalerted([a, b])) == 2
    storage.mark_alerted([a])
    remaining = storage.filter_unalerted([a, b])
    assert [s.title for s in remaining] == ["B"]


def test_mark_alerted_twice_is_safe(temp_db):
    a = story("A", "http://x/a")
    storage.mark_alerted([a])
    storage.mark_alerted([a])
    assert storage.filter_unalerted([a]) == []


def test_graph_critical_story_triggers_alert_before_email():
    alerts, digests, marked = [], [], []
    graph = build_briefing_graph(
        client=FakeClient("Critical"),
        collector=lambda n: ARTICLES,
        saver=lambda a: a,
        sender=digests.append,
        alert_sender=alerts.append,
        alert_filter=lambda s: s,
        alert_marker=marked.append,
        delay=0,
    )
    result = graph.invoke({"trace": []})
    order = [line.split(":")[0] for line in result["trace"]]
    assert order == ["collect", "summarize", "analyze", "factcheck", "claims", "rank", "alert", "email"]
    assert len(alerts) == 1 and len(alerts[0]) == 2
    assert len(marked) == 1
    assert len(digests) == 1


def test_graph_without_critical_skips_alert():
    def must_not_alert(stories):
        raise AssertionError("alert nahi jana chahiye tha")

    digests = []
    graph = build_briefing_graph(
        client=FakeClient("High"),
        collector=lambda n: ARTICLES,
        saver=lambda a: a,
        sender=digests.append,
        alert_sender=must_not_alert,
        alert_filter=lambda s: s,
        alert_marker=lambda s: None,
        delay=0,
    )
    result = graph.invoke({"trace": []})
    order = [line.split(":")[0] for line in result["trace"]]
    assert "alert" not in order
    assert len(digests) == 1

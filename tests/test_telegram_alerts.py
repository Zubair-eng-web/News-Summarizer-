from app.agents.alert_agent import (
    MAX_TELEGRAM_ALERTS,
    build_telegram_text,
    send_telegram_alert,
)
from app.core.story import Story
from app.core.telegram_notifier import TelegramNotifier
from app.graph.alerts import build_alert_graph


def make_story(title="Big quake", priority="Critical"):
    return Story(
        title=title,
        summary="Strong earthquake reported.",
        sources=[("BBC", "https://bbc.com/x"), ("Dawn", "https://dawn.com/y")],
        priority=priority,
        sentiment="negative",
        credibility="Confirmed by 2 sources",
    )


def make_notifier(sent):
    def fake_post(url, payload):
        sent.append(payload["text"])
        return 200

    return TelegramNotifier("T", "1", post=fake_post)


def test_telegram_text_has_title_summary_credibility_and_link():
    text = build_telegram_text(make_story())
    assert "BREAKING: Big quake" in text
    assert "Strong earthquake reported." in text
    assert "Confirmed by 2 sources" in text
    assert "https://bbc.com/x" in text


def test_each_story_is_sent():
    sent = []
    n = send_telegram_alert([make_story("A"), make_story("B")], notifier=make_notifier(sent))
    assert n == 2
    assert "BREAKING: A" in sent[0] and "BREAKING: B" in sent[1]


def test_disabled_notifier_sends_nothing():
    assert send_telegram_alert([make_story()], notifier=TelegramNotifier(None, None)) == 0


def test_empty_list_sends_nothing():
    sent = []
    assert send_telegram_alert([], notifier=make_notifier(sent)) == 0
    assert sent == []


def test_alerts_are_capped():
    sent = []
    stories = [make_story(f"S{i}") for i in range(MAX_TELEGRAM_ALERTS + 3)]
    assert send_telegram_alert(stories, notifier=make_notifier(sent)) == MAX_TELEGRAM_ALERTS
    assert len(sent) == MAX_TELEGRAM_ALERTS


def test_broken_notifier_never_raises():
    class Boom:
        enabled = True

        def send(self, text):
            raise RuntimeError("boom")

    assert send_telegram_alert([make_story()], notifier=Boom()) == 0


def _patch_graph(monkeypatch, story):
    monkeypatch.setattr("app.graph.alerts.quick_stories", lambda articles: [story])
    monkeypatch.setattr("app.graph.alerts.analyze_stories", lambda stories, client: None)
    monkeypatch.setattr("app.graph.alerts.check_credibility", lambda stories: None)


def test_graph_sends_email_then_telegram_then_marks(monkeypatch):
    _patch_graph(monkeypatch, make_story())
    calls = []
    graph = build_alert_graph(
        client=object(),
        collector=lambda limit: ["raw"],
        saver=lambda items: items,
        alert_sender=lambda s: calls.append("email"),
        telegram_sender=lambda s: calls.append("telegram"),
        alert_filter=lambda s: s,
        alert_marker=lambda s: calls.append("mark"),
    )
    graph.invoke({"trace": []})
    assert calls == ["email", "telegram", "mark"]


def test_graph_without_critical_story_sends_nothing(monkeypatch):
    _patch_graph(monkeypatch, make_story(priority="Low"))
    calls = []
    graph = build_alert_graph(
        client=object(),
        collector=lambda limit: ["raw"],
        saver=lambda items: items,
        alert_sender=lambda s: calls.append("email"),
        telegram_sender=lambda s: calls.append("telegram"),
        alert_filter=lambda s: s,
        alert_marker=lambda s: calls.append("mark"),
    )
    graph.invoke({"trace": []})
    assert calls == []
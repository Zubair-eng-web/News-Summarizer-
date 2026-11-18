import json
from types import SimpleNamespace

from app.collectors.rss import Article
from app.graph.alerts import build_alert_graph, quick_stories


class FakeModels:
    def __init__(self, priority):
        self.priority = priority

    def generate_content(self, **kwargs):
        n = kwargs["contents"].count("\n") + 1
        data = [{"id": i, "priority": self.priority, "sentiment": "negative"} for i in range(1, n + 1)]
        return SimpleNamespace(text=json.dumps(data))


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


def order(result):
    return [line.split(":")[0] for line in result["trace"]]


def test_quick_stories_merges_duplicates():
    stories = quick_stories(ARTICLES)
    assert len(stories) == 2
    assert len(stories[0].sources) == 2


def test_critical_story_triggers_alert():
    alerts, marked = [], []
    graph = build_alert_graph(
        client=FakeClient("Critical"),
        collector=lambda n: ARTICLES,
        saver=lambda a: a,
        alert_sender=alerts.append,
        alert_filter=lambda s: s,
        alert_marker=marked.append,
    )
    result = graph.invoke({"trace": []})
    assert order(result) == ["collect", "triage", "alert"]
    assert len(alerts) == 1 and len(alerts[0]) == 2
    assert len(marked) == 1


def test_no_critical_means_no_alert():
    def must_not_alert(stories):
        raise AssertionError("alert nahi jana chahiye tha")

    graph = build_alert_graph(
        client=FakeClient("High"),
        collector=lambda n: ARTICLES,
        saver=lambda a: a,
        alert_sender=must_not_alert,
        alert_filter=lambda s: s,
        alert_marker=lambda s: None,
    )
    result = graph.invoke({"trace": []})
    assert order(result) == ["collect", "triage"]


def test_no_new_articles_stops_early():
    def must_not_alert(stories):
        raise AssertionError("alert nahi jana chahiye tha")

    graph = build_alert_graph(
        client=FakeClient("Critical"),
        collector=lambda n: ARTICLES,
        saver=lambda a: [],
        alert_sender=must_not_alert,
    )
    result = graph.invoke({"trace": []})
    assert order(result) == ["collect"]


def test_already_alerted_story_is_not_sent_again():
    def must_not_alert(stories):
        raise AssertionError("dobara alert nahi jana chahiye tha")

    graph = build_alert_graph(
        client=FakeClient("Critical"),
        collector=lambda n: ARTICLES,
        saver=lambda a: a,
        alert_sender=must_not_alert,
        alert_filter=lambda s: [],  # sab pehle hi alert ho chuke
        alert_marker=lambda s: None,
    )
    result = graph.invoke({"trace": []})
    assert order(result) == ["collect", "triage"]

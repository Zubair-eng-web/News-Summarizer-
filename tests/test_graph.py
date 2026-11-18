import json
from types import SimpleNamespace

from app.collectors.rss import Article
from app.graph.briefing import build_briefing_graph


class FakeModels:
    def generate_content(self, **kwargs):
        prompt = kwargs["config"].system_instruction
        if "news editor" in prompt:
            n = kwargs["contents"].count("\n") + 1
            data = [{"id": i, "priority": "High", "sentiment": "neutral"} for i in range(1, n + 1)]
            return SimpleNamespace(text=json.dumps(data))
        return SimpleNamespace(text="Fake summary.")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def make(title, source):
    return Article(title=title, link=f"http://x.com/{source}/{title}", summary="", source=source)


ARTICLES = [
    make("Bank of England raises interest rate to fight inflation", "BBC"),
    make("Bank of England lifts interest rate to fight inflation", "Dawn"),
    make("Ronaldo retires from Portugal national team", "BBC"),
]


def test_graph_has_all_agents():
    nodes = set(build_briefing_graph(client=FakeClient()).get_graph().nodes)
    assert {"collect", "summarize", "analyze", "factcheck", "rank", "email"} <= nodes


def test_full_run_in_correct_order():
    sent = []
    graph = build_briefing_graph(
        client=FakeClient(),
        collector=lambda n: ARTICLES,
        saver=lambda a: a,
        sender=sent.append,
        delay=0,
    )
    result = graph.invoke({"trace": []})

    order = [line.split(":")[0] for line in result["trace"]]
    assert order == ["collect", "summarize", "analyze", "factcheck", "claims", "rank", "email"]
    assert result["sent"] is True
    assert len(sent) == 1

    stories = result["stories"]
    assert len(stories) == 2
    assert stories[0].credibility == "Confirmed by 2 sources"
    assert stories[0].priority == "High"


def test_no_new_articles_skips_everything():
    def must_not_send(stories):
        raise AssertionError("email nahi bhejni chahiye thi")

    graph = build_briefing_graph(
        client=FakeClient(),
        collector=lambda n: ARTICLES,
        saver=lambda a: [],
        sender=must_not_send,
        delay=0,
    )
    result = graph.invoke({"trace": []})
    assert not result.get("sent")
    assert "stories" not in result
    assert len(result["trace"]) == 1

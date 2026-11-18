import json
from types import SimpleNamespace

from app.collectors.rss import Article
from app.graph.briefing import build_briefing_graph

ARTICLES = [Article(title="Ronaldo retires from Portugal team", link="http://x/r", summary="", source="BBC")]


class FakeModels:
    def generate_content(self, **kwargs):
        if "news editor" in kwargs["config"].system_instruction:
            n = kwargs["contents"].count("\n") + 1
            data = [{"id": i, "priority": "High", "sentiment": "neutral"} for i in range(1, n + 1)]
            return SimpleNamespace(text=json.dumps(data))
        return SimpleNamespace(text="Fake summary.")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def build(sender, video_loader=None):
    return build_briefing_graph(
        client=FakeClient(),
        collector=lambda n: ARTICLES,
        saver=lambda a: a,
        sender=sender,
        video_loader=video_loader,
        alert_sender=lambda s: None,
        alert_filter=lambda s: s,
        alert_marker=lambda s: None,
        delay=0,
    )


def test_email_node_passes_videos():
    calls = []

    def sender(stories, videos=None):
        calls.append((stories, videos))

    result = build(sender, video_loader=lambda: [{"title": "V"}]).invoke({"trace": []})
    assert calls[0][1] == [{"title": "V"}]
    assert "1 videos" in result["trace"][-1]


def test_without_loader_sender_gets_only_stories():
    sent = []
    result = build(sent.append).invoke({"trace": []})
    assert len(sent) == 1
    assert result["sent"] is True


def test_empty_video_list_is_not_passed():
    sent = []
    build(sent.append, video_loader=lambda: []).invoke({"trace": []})
    assert len(sent) == 1

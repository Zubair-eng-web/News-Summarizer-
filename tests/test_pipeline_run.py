from types import SimpleNamespace

import pytest

from app import pipeline
from app.collectors.rss import Article


class FakeModels:
    def generate_content(self, **kwargs):
        return SimpleNamespace(text="Fake summary.")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def art(title, source, n):
    return Article(title=title, link=f"http://x.test/{n}", summary="details here", source=source)


ARTICLES = [
    art("Volcano erupts near Reykjavik overnight", "BBC", 1),
    art("Parliament votes on housing bill", "Dawn", 2),
    art("Startup raises funding for battery recycling", "TechCrunch", 3),
]


@pytest.fixture
def log(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "analyze_stories", lambda stories, client: calls.append("analyze"))
    monkeypatch.setattr(pipeline, "check_credibility", lambda stories: calls.append("credibility"))
    monkeypatch.setattr(pipeline, "check_claims", lambda stories, client: calls.append("claims"))
    monkeypatch.setattr(pipeline, "rank_stories", lambda stories: calls.append("rank") or list(stories))
    monkeypatch.setattr(pipeline, "collect_all", lambda limit: list(ARTICLES))
    return calls


def test_only_new_articles_are_processed_in_order(monkeypatch, log):
    monkeypatch.setattr(pipeline, "save_new_articles", lambda articles: [ARTICLES[0]])
    stories = pipeline.run_pipeline(client=FakeClient(), delay=0)
    assert [s.title for s in stories] == [ARTICLES[0].title]
    assert log == ["analyze", "credibility", "claims", "rank"]


def test_all_mode_processes_everything(monkeypatch, log):
    monkeypatch.setattr(pipeline, "save_new_articles", lambda articles: [])
    stories = pipeline.run_pipeline(client=FakeClient(), only_new=False, delay=0)
    assert len(stories) == 3


def test_nothing_new_returns_early_without_building_a_client(monkeypatch, log):
    def must_not_build():
        raise AssertionError("client nahi banna chahiye tha")

    monkeypatch.setattr(pipeline, "save_new_articles", lambda articles: [])
    monkeypatch.setattr(pipeline, "get_client", must_not_build)
    assert pipeline.run_pipeline(delay=0) == []
    assert log == []


def test_max_stories_limits_the_result(monkeypatch, log):
    monkeypatch.setattr(pipeline, "save_new_articles", lambda articles: [])
    stories = pipeline.run_pipeline(client=FakeClient(), only_new=False, max_stories=2, delay=0)
    assert len(stories) == 2


def test_client_is_built_when_not_given(monkeypatch, log):
    monkeypatch.setattr(pipeline, "save_new_articles", lambda articles: [ARTICLES[0]])
    monkeypatch.setattr(pipeline, "get_client", lambda: FakeClient())
    assert len(pipeline.run_pipeline(delay=0)) == 1


def test_build_stories_keeps_evidence_and_sleeps_between_stories(monkeypatch):
    sleeps = []
    monkeypatch.setattr(pipeline.time, "sleep", sleeps.append)
    stories = pipeline.build_stories(ARTICLES, client=FakeClient(), delay=2)
    assert sleeps == [2, 2, 2]
    first = [s for s in stories if s.sources[0][0] == "BBC"][0]
    assert first.evidence[0][0] == "BBC"
    assert first.evidence[0][1].startswith("Volcano erupts near Reykjavik overnight.")

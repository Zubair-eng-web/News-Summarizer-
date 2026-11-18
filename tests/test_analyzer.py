from types import SimpleNamespace

from app.agents.analyzer import analyze_stories, parse_analysis
from app.agents.email_agent import build_html
from app.agents.ranker import rank_stories
from app.core.story import Story


class FakeModels:
    def __init__(self, text):
        self.text = text

    def generate_content(self, **kwargs):
        return SimpleNamespace(text=self.text)


class FakeClient:
    def __init__(self, text):
        self.models = FakeModels(text)


def story(title, n_sources=1, priority="Medium"):
    return Story(
        title=title,
        summary="s",
        sources=[("X", f"http://x.com/{i}") for i in range(n_sources)],
        priority=priority,
    )


def test_parse_valid_json():
    text = '[{"id": 1, "priority": "High", "sentiment": "negative"}]'
    assert parse_analysis(text) == {1: ("High", "negative")}


def test_parse_json_inside_code_fence():
    text = '```json\n[{"id": 2, "priority": "Low", "sentiment": "positive"}]\n```'
    assert parse_analysis(text) == {2: ("Low", "positive")}


def test_parse_invalid_json_returns_empty():
    assert parse_analysis("this is not json") == {}
    assert parse_analysis("") == {}


def test_parse_invalid_values_get_defaults():
    text = '[{"id": 1, "priority": "Urgent", "sentiment": "angry"}]'
    assert parse_analysis(text) == {1: ("Medium", "neutral")}


def test_analyze_sets_fields():
    stories = [story("A"), story("B")]
    text = (
        '[{"id":1,"priority":"critical","sentiment":"Negative"},'
        '{"id":2,"priority":"Low","sentiment":"positive"}]'
    )
    analyze_stories(stories, client=FakeClient(text))
    assert (stories[0].priority, stories[0].sentiment) == ("Critical", "negative")
    assert (stories[1].priority, stories[1].sentiment) == ("Low", "positive")


def test_analyze_fallback_on_bad_response():
    stories = [story("A")]
    analyze_stories(stories, client=FakeClient("not json"))
    assert (stories[0].priority, stories[0].sentiment) == ("Medium", "neutral")


def test_rank_by_priority():
    ranked = rank_stories(
        [story("low", priority="Low"), story("crit", priority="Critical"), story("high", priority="High")]
    )
    assert [s.title for s in ranked] == ["crit", "high", "low"]


def test_rank_tiebreak_by_sources():
    ranked = rank_stories(
        [story("one", 1, "High"), story("three", 3, "High"), story("two", 2, "High")]
    )
    assert [s.title for s in ranked] == ["three", "two", "one"]


def test_email_shows_priority_and_counts():
    html = build_html([story("A", priority="Critical"), story("B", priority="Low")], "d")
    assert "Critical" in html
    assert "Critical: 1 | Low: 1" in html

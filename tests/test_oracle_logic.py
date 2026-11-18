import importlib
from datetime import datetime

import pytest

from dashboard.oracle import components as ui
from dashboard.oracle import logic, status

STORIES = [
    {"title": "Flood hits Sindh", "summary": "Heavy rain", "priority": "High",
     "sentiment": "negative", "created_at": "2026-11-17T10:00:00",
     "sources": [{"source": "Dawn", "link": "https://d.example/1"}], "claims": []},
    {"title": "AI chip launch", "summary": "New GPU", "priority": "Critical",
     "sentiment": "positive", "created_at": "2026-11-18T09:00:00",
     "sources": [{"source": "TechCrunch", "link": "https://t.example/1"},
                 {"source": "BBC World", "link": "https://b.example/1"}],
     "claims": [{"claim": "x", "status": "disputed"}]},
    {"title": "Local festival", "summary": "Music", "priority": "Low",
     "sentiment": "neutral", "created_at": "2026-11-18T08:00:00",
     "sources": [{"source": "Dawn", "link": ""}], "claims": []},
]


def test_filter_search_and_sentiment():
    assert [s["title"] for s in logic.filter_stories(STORIES, query="gpu")] == ["AI chip launch"]
    assert len(logic.filter_stories(STORIES, sentiment="negative")) == 1
    assert len(logic.filter_stories(STORIES, source="Dawn")) == 2


def test_sort_latest_and_priority():
    assert logic.filter_stories(STORIES)[0]["title"] == "AI chip launch"
    by_priority = logic.filter_stories(STORIES, sort="Priority")
    assert [s["priority"] for s in by_priority] == ["Critical", "High", "Low"]


def test_counts():
    assert logic.source_counts(STORIES)[0] == {"source": "Dawn", "stories": 2}
    assert logic.sentiment_counts(STORIES)[0] == {"sentiment": "positive", "stories": 1}
    days = logic.count_by_day(STORIES)
    assert days == [{"day": "2026-11-17", "stories": 1}, {"day": "2026-11-18", "stories": 2}]
    assert logic.source_names(STORIES) == ["BBC World", "Dawn", "TechCrunch"]


def test_filter_videos():
    videos = [{"title": "AI news", "summary": "", "channel": "A"},
              {"title": "Cricket", "summary": "", "channel": "B"}]
    assert len(logic.filter_videos(videos, query="ai")) == 1
    assert len(logic.filter_videos(videos, channel="B")) == 1


def test_freshness_helpers():
    now = datetime(2026, 11, 18, 12, 0, 0)
    assert status.age_hours("2026-11-18T10:00:00", now) == pytest.approx(2.0)
    assert status.age_hours(None) is None
    assert status.age_hours("not a date") is None
    assert status.freshness_label(None) == "No data yet"
    assert status.freshness_label(0.2) == "Under 1 hour ago"
    assert status.freshness_label(5.7) == "5 h ago"
    assert status.freshness_label(100) == "4 days ago"
    assert status.freshness_state(5) == "ok"
    assert status.freshness_state(50) == "warn"
    assert status.freshness_state(200) == "bad"
    assert status.freshness_state(None) == "neutral"


def test_build_checks_is_honest():
    checks = {c["label"]: c for c in status.build_checks(True, {"alerts_sent": 4}, None)}
    assert checks["API"]["state"] == "ok"
    assert checks["Breaking alerts sent"]["value"] == "4"
    assert checks["Collector"]["value"] == "Not monitored yet"
    down = {c["label"]: c for c in status.build_checks(False, None, None)}
    assert down["API"]["state"] == "bad" and down["Database"]["state"] == "bad"


def test_html_builders_escape_and_flag():
    assert "&lt;b&gt;" in ui.kpi_html("<b>", 1, "#fff")
    assert "Details differ" in ui.story_badges_html(STORIES[1])
    assert "Details differ" not in ui.story_badges_html(STORIES[0])
    assert "Online" in ui.status_grid_html(status.build_checks(True, {"a": 1}, None))
    assert "Nothing" in ui.empty_html("Nothing", "hint")
    assert "AI chip" in ui.story_row_html(STORIES[1])


@pytest.mark.parametrize("name", ["overview", "feed", "research", "misc", "sidebar", "data"])
def test_page_modules_import(name):
    importlib.import_module(f"dashboard.oracle.{name}")
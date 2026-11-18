from datetime import datetime

from dashboard.oracle import report

STORIES = [
    {"title": "Big quake <b>hits</b>", "summary": "Strong quake.", "priority": "Critical",
     "sentiment": "negative", "credibility": "Confirmed by 2 sources", "category": "Disaster",
     "sources": [{"source": "BBC", "link": "https://bbc.com/a"},
                 {"source": "Bad", "link": "javascript:alert(1)"}]},
    {"title": "Chip launch", "summary": "New chip.", "priority": "Low", "sentiment": "positive",
     "credibility": "Single source", "category": "Technology", "sources": []},
]
VIDEOS = [{"title": "Talk", "link": "https://youtu.be/x", "channel": "Chan", "takeaway": "Key"}]


def test_summary_counts():
    c = report.summary_counts(STORIES)
    assert c["total"] == 2
    assert c["priority"]["Critical"] == 1 and c["priority"]["Medium"] == 0
    assert c["category"]["Disaster"] == 1


def test_markdown_has_sections_and_blocks_bad_links():
    md = report.build_markdown("Daily", STORIES, VIDEOS, "2026-11-18 10:00")
    assert "## Critical stories (1)" in md and "## Low stories (1)" in md
    assert "[BBC](https://bbc.com/a)" in md
    assert "javascript:" not in md
    assert "YouTube highlights (1)" in md


def test_markdown_empty():
    md = report.build_markdown("Daily", [], [], "now")
    assert "No stories in this period." in md
    assert "No video summaries in this period." in md


def test_html_escapes_text_and_links():
    html = report.build_html("Daily", STORIES, VIDEOS, "now")
    assert "<b>hits</b>" not in html
    assert "&lt;b&gt;hits&lt;/b&gt;" in html
    assert "javascript:" not in html


def test_recent_videos_filters_by_date():
    now = datetime(2026, 11, 18, 12, 0)
    vids = [
        {"title": "new", "published": "2026-11-18T08:00:00"},
        {"title": "old", "published": "2026-11-01T08:00:00"},
        {"title": "nodate", "published": None},
    ]
    names = [v["title"] for v in report.recent_videos(vids, 24, now)]
    assert names == ["new", "nodate"]
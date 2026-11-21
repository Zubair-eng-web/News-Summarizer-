import pytest

pytest.importorskip("fpdf")

from dashboard.oracle.pdf_export import _text, build_pdf  # noqa: E402

STORIES = [
    {"title": "Big news \u2019 today", "priority": "Critical", "sentiment": "negative",
     "credibility": "Confirmed by 2 sources", "summary": "Summary \u0627\u0631\u062f\u0648 text",
     "sources": [{"source": "BBC", "link": "https://a.example"}]},
    {"title": "x" * 300, "priority": "Low", "summary": "https://" + "a" * 200},
]
VIDEOS = [{"title": "Video", "channel": "Chan", "takeaway": "Learn this"}]


def test_pdf_is_valid():
    data = build_pdf("Daily Report", STORIES, VIDEOS, "2026-11-21 10:00")
    assert data.startswith(b"%PDF") and len(data) > 500


def test_pdf_empty_report():
    assert build_pdf("Empty", [], [], "now").startswith(b"%PDF")


def test_text_cleans_and_wraps():
    assert "\u2019" not in _text("it\u2019s")
    assert all(len(w) <= 60 for w in _text("z" * 200).split(" "))

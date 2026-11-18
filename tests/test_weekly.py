from datetime import datetime
from types import SimpleNamespace

from app.weekly import build_weekly_report, generate_overview, trending_terms

NOW = datetime(2026, 11, 8, 12, 0)
START = datetime(2026, 11, 1, 12, 0)


def story(title, priority="Medium", sentiment="neutral", sources=1, summary="s"):
    return {
        "title": title,
        "summary": summary,
        "priority": priority,
        "sentiment": sentiment,
        "credibility": "Single source",
        "sources": [{"source": f"S{i}", "link": f"http://x/{i}"} for i in range(sources)],
    }


CUR = [
    story("Iran war talks stall", "Critical", "negative", sources=2, summary="Talks stall."),
    story("Iran war talks stall", "Critical", "negative", sources=2, summary="Older copy."),
    story("Central bank raises rates", "High", "neutral"),
    story("Football cup final", "Low", "positive"),
    story("Stock markets fall", "High", "negative", sources=3),
]
PREV = [story("Old story one"), story("Old story two", "Low")]


def loader(start, end):
    return CUR if start == START else PREV


class FakeModels:
    def __init__(self, text="  This week was busy.  "):
        self.text = text
        self.last = ""

    def generate_content(self, **kwargs):
        self.last = kwargs["contents"]
        return SimpleNamespace(text=self.text)


class FakeClient:
    def __init__(self, text="  This week was busy.  "):
        self.models = FakeModels(text)


class BrokenClient:
    class models:
        @staticmethod
        def generate_content(**kwargs):
            raise RuntimeError("boom")


class MustNotCallClient:
    class models:
        @staticmethod
        def generate_content(**kwargs):
            raise AssertionError("Gemini call nahi honi chahiye thi")


def test_trending_prefers_bigram_over_its_parts():
    docs = [
        "Iran war escalates as talks stall",
        "Oil prices rise amid Iran war fears",
        "Parliament debates Iran war funding",
        "Local football team wins cup",
    ]
    result = trending_terms(docs, [])
    assert [t["term"] for t in result] == ["iran war"]
    assert result[0]["count"] == 3
    assert result[0]["status"] == "new"


def test_trending_status_compared_with_previous_week():
    current = ["inflation is up"] * 4 + ["wheat is up"] * 2 + ["drought is up"] * 2 + ["rates is up"] * 2
    previous = ["inflation is up"] + ["wheat is up"] * 2 + ["rates is up"] * 4
    by_term = {t["term"]: t for t in trending_terms(current, previous, top_n=20)}
    assert by_term["inflation"]["status"] == "rising"
    assert by_term["wheat"]["status"] == "steady"
    assert by_term["drought"]["status"] == "new"
    assert by_term["rates"]["status"] == "falling"
    assert by_term["inflation"]["previous"] == 1


def test_trending_ignores_terms_below_min_count():
    assert trending_terms(["Parliament debates budget"], []) == []


def test_report_counts_dedups_and_ranks():
    report = build_weekly_report(
        now=NOW, stories_loader=loader, videos_loader=lambda s, e: [], overview=False
    )
    assert report["total"] == 4  # duplicate title ek hi ginti
    assert report["previous_total"] == 2
    assert report["has_previous"] is True
    assert report["priority"]["Critical"] == {"count": 1, "previous": 0}
    assert report["priority"]["High"] == {"count": 2, "previous": 0}
    assert report["priority"]["Medium"] == {"count": 0, "previous": 1}
    assert report["sentiment"]["negative"]["count"] == 2
    assert [s["title"] for s in report["top_stories"]] == [
        "Iran war talks stall",
        "Stock markets fall",
        "Central bank raises rates",
        "Football cup final",
    ]
    assert report["start"] == START.isoformat()
    assert report["end"] == NOW.isoformat()
    assert report["top_stories"][0]["summary"] == "Talks stall."  # nayi copy rakhi gayi


def test_report_without_previous_week_data():
    report = build_weekly_report(
        now=NOW,
        stories_loader=lambda s, e: CUR if s == START else [],
        videos_loader=lambda s, e: [],
        overview=False,
    )
    assert report["has_previous"] is False
    assert report["previous_total"] == 0


def test_overview_is_generated_from_top_stories():
    client = FakeClient()
    report = build_weekly_report(
        now=NOW, stories_loader=loader, videos_loader=lambda s, e: [], client=client
    )
    assert report["overview"] == "This week was busy."
    assert "Iran war talks stall" in client.models.last


def test_overview_can_be_turned_off():
    report = build_weekly_report(
        now=NOW,
        stories_loader=loader,
        videos_loader=lambda s, e: [],
        client=MustNotCallClient(),
        overview=False,
    )
    assert report["overview"] == ""


def test_overview_failure_returns_empty_string():
    assert generate_overview([story("A")], [], client=BrokenClient()) == ""


def test_empty_week_makes_no_gemini_call():
    report = build_weekly_report(
        now=NOW,
        stories_loader=lambda s, e: [],
        videos_loader=lambda s, e: [],
        client=MustNotCallClient(),
    )
    assert report["total"] == 0
    assert report["top_stories"] == []
    assert report["overview"] == ""


def test_videos_with_transcript_come_first_and_are_limited():
    videos = [{"video_id": f"v{i}", "has_transcript": i % 2 == 0} for i in range(6)]
    report = build_weekly_report(
        now=NOW, stories_loader=loader, videos_loader=lambda s, e: videos, overview=False
    )
    assert [v["video_id"] for v in report["videos"]] == ["v0", "v2", "v4", "v1", "v3"]

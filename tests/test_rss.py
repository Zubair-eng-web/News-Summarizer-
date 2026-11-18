import pytest

from app.collectors import rss
from app.collectors.rss import Article, clean_html, collect_all, fetch_feed, parse_date


class FakeFeed:
    def __init__(self, entries):
        self.entries = entries


def make_entry(i):
    return {
        "title": f"<b>Title {i}</b>",
        "link": f"https://example.com/{i}",
        "summary": "<p>Body text</p>",
        "published_parsed": (2026, 1, 1, 10, 0, 0, 0, 1, 0),
    }


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(rss, "RETRY_DELAY", 0)
    monkeypatch.setattr(rss, "load_extra_feeds", dict)


def test_clean_html():
    assert clean_html("<p>Hello <b>World</b></p>") == "Hello World"
    assert clean_html("") == ""


def test_parse_date_handles_missing():
    assert parse_date({}) is None
    assert parse_date({"published_parsed": (2026, 1, 1, 10, 0, 0, 0, 1, 0)}).year == 2026


def test_fetch_feed_builds_articles(monkeypatch):
    monkeypatch.setattr(rss.feedparser, "parse", lambda url: FakeFeed([make_entry(i) for i in range(5)]))
    articles = fetch_feed("Test", "https://x.test/rss", limit=3)
    assert len(articles) == 3
    assert isinstance(articles[0], Article)
    assert articles[0].title == "Title 0"
    assert articles[0].link.startswith("http")
    assert articles[0].summary == "Body text"
    assert articles[0].source == "Test"


def test_fetch_feed_retries_once(monkeypatch):
    calls = {"n": 0}

    def fake_parse(url):
        calls["n"] += 1
        return FakeFeed([]) if calls["n"] == 1 else FakeFeed([make_entry(1)])

    monkeypatch.setattr(rss.feedparser, "parse", fake_parse)
    assert len(fetch_feed("Test", "https://x.test/rss")) == 1
    assert calls["n"] == 2


def test_fetch_feed_returns_empty_on_error(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(rss.feedparser, "parse", boom)
    assert fetch_feed("Test", "https://x.test/rss") == []


def test_collect_all_survives_one_failing_source(monkeypatch):
    def fake_parse(url):
        if "dawn" in url:
            raise RuntimeError("blocked")
        return FakeFeed([make_entry(i) for i in range(5)])

    monkeypatch.setattr(rss.feedparser, "parse", fake_parse)
    articles = collect_all(limit_per_feed=3)
    assert len(articles) == 3 * (len(rss.FEEDS) - 1)
    assert all(a.source != "Dawn" for a in articles)

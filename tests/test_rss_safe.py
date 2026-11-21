import feedparser

from app.collectors import rss
from app.core.safe_fetch import FetchError

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Hello</title><link>https://a.example/1</link><description>d</description></item>
</channel></rss>"""


def test_safe_fetch_feed_parses(monkeypatch):
    monkeypatch.setattr(rss.time, "sleep", lambda s: None)
    got = rss.fetch_feed("X (custom)", "https://a.example/f", 5, safe=True, fetcher=lambda u: RSS)
    assert [a.title for a in got] == ["Hello"]


def test_safe_fetch_blocked_returns_empty(monkeypatch):
    monkeypatch.setattr(rss.time, "sleep", lambda s: None)

    def blocked(url):
        raise FetchError("private")

    assert rss.fetch_feed("X (custom)", "http://10.0.0.1/f", 5, safe=True, fetcher=blocked) == []


def test_builtin_feed_still_uses_feedparser(monkeypatch):
    monkeypatch.setattr(rss.time, "sleep", lambda s: None)
    real_parse = feedparser.parse
    monkeypatch.setattr(rss.feedparser, "parse", lambda url: real_parse(RSS))
    assert len(rss.fetch_feed("BBC World", "https://a.example/f", 5)) == 1

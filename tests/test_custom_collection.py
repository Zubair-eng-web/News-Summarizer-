from app.collectors import rss, youtube
from app.core.video import Video


class FakeFeed:
    def __init__(self, entries):
        self.entries = entries


def test_collect_all_includes_extra_feeds(monkeypatch):
    entry = {
        "title": "T",
        "link": "https://e.test/1",
        "summary": "S",
        "published_parsed": (2026, 1, 1, 10, 0, 0, 0, 1, 0),
    }
    monkeypatch.setattr(rss.feedparser, "parse", lambda url: FakeFeed([entry]))
    articles = rss.collect_all(
        limit_per_feed=1, extra_feeds={"Mine (custom)": "https://mine.test/rss"}
    )
    assert len(articles) == len(rss.FEEDS) + 1
    assert "Mine (custom)" in {a.source for a in articles}


def test_collect_videos_merges_custom_channels(monkeypatch):
    cid = "UC" + "b" * 22
    monkeypatch.setattr(youtube, "load_extra_channels", lambda: {"Mine (custom)": cid})

    def fetcher(name, channel_id, limit):
        short = channel_id[:11]
        return [
            Video(
                video_id=short,
                title=f"Video {name}",
                link=f"https://youtu.be/{short}",
                channel=name,
                published=None,
                description="",
            )
        ]

    merged = youtube.collect_videos(1, fetcher=fetcher, include_custom=True)
    assert "Mine (custom)" in {v.channel for v in merged}
    plain = youtube.collect_videos(1, fetcher=fetcher)
    assert "Mine (custom)" not in {v.channel for v in plain}
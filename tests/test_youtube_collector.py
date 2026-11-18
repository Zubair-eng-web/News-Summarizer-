from datetime import datetime
from types import SimpleNamespace

import feedparser
import pytest

from app.collectors.youtube import (
    TranscriptError,
    collect_videos,
    extract_video_id,
    fetch_channel,
    fetch_transcript,
)
from app.core.video import Video

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <title>BBC News</title>
 <entry>
  <id>yt:video:abc123DEF45</id>
  <yt:videoId>abc123DEF45</yt:videoId>
  <title>Big news today</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=abc123DEF45"/>
  <published>2026-11-05T10:00:00+00:00</published>
  <media:group><media:description>Some description</media:description></media:group>
 </entry>
 <entry>
  <id>yt:video:xyz987UVW65</id>
  <yt:videoId>xyz987UVW65</yt:videoId>
  <title>Second   video</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=xyz987UVW65"/>
  <published>2026-11-04T09:30:00+00:00</published>
 </entry>
</feed>"""


class FakeApi:
    def __init__(self, snippets=None, error=None):
        self.snippets = snippets or []
        self.error = error

    def fetch(self, video_id, languages):
        if self.error:
            raise self.error
        return self.snippets


def make(video_id, hour):
    return Video(video_id, video_id, f"https://youtu.be/{video_id}", "C", datetime(2026, 11, 5, hour))


def test_extract_video_id_from_various_urls():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=5") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("not a video") is None
    assert extract_video_id("") is None


def test_fetch_channel_parses_feed():
    videos = fetch_channel("BBC News", "UC1", limit=5, parser=lambda url: feedparser.parse(FEED))
    assert [v.video_id for v in videos] == ["abc123DEF45", "xyz987UVW65"]
    assert videos[0].title == "Big news today"
    assert videos[1].title == "Second video"
    assert videos[0].channel == "BBC News"
    assert videos[0].link == "https://www.youtube.com/watch?v=abc123DEF45"
    assert videos[0].published == datetime(2026, 11, 5, 10, 0, 0)


def test_fetch_channel_handles_errors_and_empty_feed():
    def boom(url):
        raise RuntimeError("network down")

    assert fetch_channel("X", "UC1", parser=boom) == []
    assert fetch_channel("X", "UC1", parser=lambda url: SimpleNamespace(entries=[])) == []


def test_fetch_transcript_joins_and_cleans_text():
    api = FakeApi(
        [
            SimpleNamespace(text="Hello [Music] world", start=0.0),
            SimpleNamespace(text="  second   line ", start=2.0),
            {"text": "third"},
        ]
    )
    assert fetch_transcript("abc123DEF45", api=api) == "Hello world second line third"


def test_fetch_transcript_wraps_errors():
    api = FakeApi(error=RuntimeError("blocked"))
    with pytest.raises(TranscriptError, match="RuntimeError"):
        fetch_transcript("abc123DEF45", api=api)


def test_fetch_transcript_empty_raises():
    api = FakeApi([SimpleNamespace(text="[Music]", start=0.0)])
    with pytest.raises(TranscriptError, match="khali"):
        fetch_transcript("abc123DEF45", api=api)


def test_collect_videos_sorts_newest_first_and_dedups():
    def fake_fetcher(name, channel_id, limit):
        return {
            "A": [make("v1", 8), make("v2", 12)],
            "B": [make("v2", 12), make("v3", 10)],
        }[name]

    videos = collect_videos(2, channels={"A": "1", "B": "2"}, fetcher=fake_fetcher)
    assert [v.video_id for v in videos] == ["v2", "v3", "v1"]

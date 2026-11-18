from datetime import datetime

from app.agents.video_agent import SYSTEM_PROMPT
from app.collectors.youtube import collect_videos, is_short
from app.core.video import Video


def make(video_id, title="T", link=None):
    return Video(video_id, title, link or f"https://youtu.be/{video_id}", "C", datetime(2026, 11, 5, 10))


def fetcher(name, channel_id, limit):
    videos = [
        make("s1", link="https://www.youtube.com/shorts/s1"),
        make("s2", title="Quick clip #Shorts"),
        make("v1"),
        make("v2"),
        make("v3"),
    ]
    return videos[:limit]


def test_is_short_detects_link_and_hashtag():
    assert is_short(make("a", link="https://www.youtube.com/shorts/abc")) is True
    assert is_short(make("b", title="Big news #Shorts")) is True
    assert is_short(make("c")) is False


def test_collect_videos_skips_shorts_and_looks_deeper():
    result = collect_videos(2, channels={"A": "1"}, fetcher=fetcher)
    assert [v.video_id for v in result] == ["v1", "v2"]


def test_collect_videos_can_include_shorts():
    result = collect_videos(2, channels={"A": "1"}, fetcher=fetcher, include_shorts=True)
    assert [v.video_id for v in result] == ["s1", "s2"]


def test_prompt_warns_about_misspelled_names():
    assert "misspell" in SYSTEM_PROMPT

from app.collectors import youtube
from app.core import source_health
from app.core.video import Video


def test_collect_videos_records_each_channel(monkeypatch):
    calls = []
    monkeypatch.setattr(source_health, "record", lambda *a, **k: calls.append(a))

    def fake(name, channel_id, limit):
        if name == "A":
            return [Video(video_id="abcdefghijk", title="t", link="https://y/1",
                          channel="A", published=None, description="")]
        return []

    result = youtube.collect_videos(channels={"A": "id1", "B": "id2"}, fetcher=fake,
                                    include_custom=False)
    assert len(result) == 1
    assert calls[0][:4] == ("A", "youtube", True, 1)
    assert calls[1][:3] == ("B", "youtube", False)
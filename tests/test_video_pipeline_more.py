from datetime import datetime
from types import SimpleNamespace

from app import video_pipeline
from app.core.video import Video
from app.video_pipeline import run_video_pipeline

JSON_REPLY = '{"summary": "S", "key_points": ["k"], "takeaway": "t"}'


class FakeModels:
    def generate_content(self, **kwargs):
        return SimpleNamespace(text=JSON_REPLY)


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def vid(i):
    return Video(f"id{i}", f"Title {i}", f"https://youtu.be/id{i}", "BBC", datetime(2026, 11, 5, i), "desc")


def run(**kwargs):
    saved = []
    options = dict(
        client=FakeClient(),
        collector=lambda n: [vid(1), vid(2), vid(3)],
        transcript_fetcher=lambda video_id: "some transcript",
        known_ids_loader=lambda: set(),
        saver=saved.append,
        delay=0,
    )
    options.update(kwargs)
    return run_video_pipeline(**options), saved


def test_delay_sleeps_between_videos_but_not_after_the_last(monkeypatch):
    sleeps = []
    monkeypatch.setattr(video_pipeline.time, "sleep", sleeps.append)
    results, _ = run(delay=2)
    assert len(results) == 3
    assert sleeps == [2, 2]


def test_only_new_false_summarizes_known_videos_again():
    results, saved = run(only_new=False, known_ids_loader=lambda: {"id1", "id2", "id3"})
    assert len(results) == 3
    assert len(saved) == 1

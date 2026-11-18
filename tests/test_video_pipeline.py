from datetime import datetime
from types import SimpleNamespace

from app import video_pipeline
from app.collectors.youtube import TranscriptError
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


def test_only_new_videos_are_summarized_and_saved():
    results, saved = run(known_ids_loader=lambda: {"id1"})
    assert [r.video_id for r in results] == ["id2", "id3"]
    assert len(saved) == 1 and len(saved[0]) == 2
    assert results[0].has_transcript is True
    assert results[0].key_points == ["k"]


def test_transcript_failure_falls_back_to_description():
    def no_transcript(video_id):
        raise TranscriptError("blocked")

    results, saved = run(transcript_fetcher=no_transcript)
    assert len(results) == 3
    assert all(r.has_transcript is False for r in results)
    assert len(saved) == 1


def test_max_videos_limit():
    results, _ = run(max_videos=2)
    assert len(results) == 2


def test_nothing_new_returns_early(monkeypatch):
    def must_not_build_client():
        raise AssertionError("client nahi banna chahiye tha")

    monkeypatch.setattr(video_pipeline, "get_client", must_not_build_client)
    results, saved = run(client=None, known_ids_loader=lambda: {"id1", "id2", "id3"})
    assert results == []
    assert saved == []

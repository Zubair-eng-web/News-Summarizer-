from app import scheduler
from app.core.config import settings
from app.scheduler import run_digest, run_videos


def test_digest_runs_video_step_first_and_passes_loader(monkeypatch):
    monkeypatch.setattr(settings, "include_videos", True)
    monkeypatch.setattr(
        scheduler, "get_recent_videos", lambda limit, hours: [{"limit": limit, "hours": hours}]
    )
    order, captured = [], {}

    def video_job():
        order.append("videos")

    def runner(**kwargs):
        order.append("digest")
        captured.update(kwargs)
        return {"trace": []}

    run_digest(runner=runner, video_job=video_job)
    assert order == ["videos", "digest"]
    loaded = captured["video_loader"]()
    assert loaded[0]["hours"] == 24
    assert loaded[0]["limit"] == settings.video_max_per_digest


def test_video_step_failure_does_not_block_digest(monkeypatch):
    monkeypatch.setattr(settings, "include_videos", True)
    captured = {}

    def broken_video_job():
        raise RuntimeError("youtube down")

    def runner(**kwargs):
        captured.update(kwargs)
        return {"trace": []}

    run_digest(runner=runner, video_job=broken_video_job)
    assert "video_loader" in captured


def test_videos_disabled_skips_video_step():
    calls, captured = [], {}

    def runner(**kwargs):
        captured.update(kwargs)
        return {"trace": []}

    run_digest(runner=runner, video_job=lambda: calls.append("videos"))
    assert calls == []
    assert "video_loader" not in captured


def test_run_videos_uses_max_from_settings():
    seen = {}

    def fake_pipeline(**kwargs):
        seen.update(kwargs)
        return []

    assert run_videos(runner=fake_pipeline) == []
    assert seen["max_videos"] == settings.video_max_per_digest

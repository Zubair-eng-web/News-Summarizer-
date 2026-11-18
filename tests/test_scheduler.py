from app.core.config import settings
from app.core.storage import get_undigested_articles, mark_digested, save_stories
from app.scheduler import _lock, is_busy, parse_time, run_digest, safe_run


def test_parse_time():
    assert parse_time("08:30") == (8, 30)
    assert parse_time(" 21:05 ") == (21, 5)


def test_safe_run_returns_true_on_success():
    assert safe_run(lambda: None, "ok-job") is True


def test_safe_run_catches_errors():
    def boom():
        raise RuntimeError("fail")

    assert safe_run(boom, "bad-job") is False


def test_run_digest_wires_selector_marker_and_saver():
    captured = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return {"trace": ["collect: x"]}

    run_digest(runner=fake_runner)
    assert captured["selector"] is get_undigested_articles
    assert captured["digest_marker"] is mark_digested
    assert captured["story_saver"] is save_stories


def test_run_digest_all_mode():
    captured = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return {"trace": []}

    run_digest(runner=fake_runner, include_all=True)
    assert captured["only_new"] is False
    assert captured["story_saver"] is save_stories
    assert "selector" not in captured


def test_is_busy_reflects_lock():
    assert is_busy() is False
    with _lock:
        assert is_busy() is True


def test_alert_interval_default_is_positive():
    assert settings.alert_interval_minutes > 0

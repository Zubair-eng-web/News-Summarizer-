import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import scheduler
from app.api.middleware import add_http_middleware
from app.core import error_alerts
from app.core.config import settings


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    error_alerts.reset()
    monkeypatch.setattr(settings, "error_alerts", True)
    monkeypatch.setattr(settings, "error_alert_cooldown_minutes", 60)
    yield
    error_alerts.reset()


def test_report_is_noop_until_installed():
    assert error_alerts.report("x", "y") is False


def test_same_error_sent_once_per_cooldown():
    calls = []
    send = lambda subject, text: calls.append(subject)  # noqa: E731
    assert error_alerts.report("Digest fail", "a", sender=send, now=1000.0) is True
    assert error_alerts.report("Digest fail", "a", sender=send, now=1100.0) is False
    assert error_alerts.report("Digest fail", "a", sender=send, now=1000.0 + 3601) is True
    assert calls == ["[ALERT] Digest fail", "[ALERT] Digest fail"]


def test_different_errors_are_not_blocked_by_each_other():
    calls = []
    send = lambda subject, text: calls.append(subject)  # noqa: E731
    assert error_alerts.report("A", sender=send, now=1.0)
    assert error_alerts.report("B", sender=send, now=2.0)
    assert len(calls) == 2


def test_sender_failure_never_raises():
    def boom(subject, text):
        raise RuntimeError("telegram down")

    assert error_alerts.report("X", "y", sender=boom, now=1.0) is False


def test_zero_cooldown_allows_repeats(monkeypatch):
    monkeypatch.setattr(settings, "error_alert_cooldown_minutes", 0)
    calls = []
    send = lambda subject, text: calls.append(1)  # noqa: E731
    assert error_alerts.report("X", sender=send, now=1.0)
    assert error_alerts.report("X", sender=send, now=2.0)
    assert len(calls) == 2


def test_global_hourly_cap():
    calls = []
    send = lambda subject, text: calls.append(subject)  # noqa: E731
    results = [error_alerts.report(f"err {i}", sender=send, now=float(i)) for i in range(15)]
    assert results.count(True) == error_alerts.MAX_PER_HOUR == len(calls)


def test_install_is_skipped_under_pytest_unless_forced():
    assert error_alerts.install(sender=lambda s, t: None) is False
    assert error_alerts.report("X") is False
    assert error_alerts.install(sender=lambda s, t: None, force=True) is True


def test_install_respects_setting(monkeypatch):
    monkeypatch.setattr(settings, "error_alerts", False)
    assert error_alerts.install(sender=lambda s, t: None, force=True) is False


def test_http_500_triggers_alert_without_leaking_details():
    calls = []
    error_alerts.install(sender=lambda subject, text: calls.append((subject, text)), force=True)
    app = FastAPI()
    add_http_middleware(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    response = TestClient(app).get("/boom")
    assert response.status_code == 500
    assert len(calls) == 1
    subject, text = calls[0]
    assert "500" in subject and "/boom" in subject
    assert "RuntimeError" in text and "secret internal detail" not in text


def test_failed_job_triggers_alert():
    calls = []
    error_alerts.install(sender=lambda subject, text: calls.append(subject), force=True)
    assert scheduler.safe_run(lambda: 1 / 0, "Digest") is False
    assert calls == ["[ALERT] Digest fail hui"]

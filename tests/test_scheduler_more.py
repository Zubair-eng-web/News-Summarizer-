import sys

import pytest

from app import scheduler
from app.core.config import settings


@pytest.fixture(autouse=True)
def quiet_settings(monkeypatch):
    monkeypatch.setattr(settings, "include_videos", False)
    monkeypatch.setattr(settings, "digest_time", "08:00")
    monkeypatch.setattr(settings, "alert_interval_minutes", 30)
    monkeypatch.setattr(settings, "weekly_day", "sun")
    monkeypatch.setattr(settings, "weekly_time", "09:00")


# ---------- run_* helpers ----------
def test_run_weekly_and_run_alerts_return_the_runner_result():
    assert scheduler.run_weekly(runner=lambda: {"ok": 1}) == {"ok": 1}
    assert scheduler.run_alerts(runner=lambda: {"trace": ["x"]}) == {"trace": ["x"]}


def test_run_user_digests_is_off_without_auth_secret(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "")
    called = []
    result = scheduler.run_user_digests(sender=lambda **kw: called.append(kw))
    assert result == {"sent": 0, "skipped": 0, "failed": 0}
    assert called == []


def test_run_user_digests_only_sends_scheduled_ones(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    seen = []

    def sender(**kwargs):
        seen.append(kwargs)
        return {"sent": 1, "skipped": 0, "failed": 0}

    assert scheduler.run_user_digests(sender=sender)["sent"] == 1
    assert seen == [{"only_scheduled": True}]


# ---------- user digests after the main digest ----------
def test_user_digests_follow_a_sent_digest(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    calls = []
    monkeypatch.setattr(
        scheduler, "send_user_digests", lambda: calls.append(1) or {"sent": 1, "skipped": 0, "failed": 0}
    )
    scheduler.run_digest(runner=lambda **kw: {"sent": True, "trace": []})
    assert calls == [1]


def test_user_digests_are_skipped_when_nothing_was_sent(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    calls = []
    monkeypatch.setattr(scheduler, "send_user_digests", lambda: calls.append(1))
    scheduler.run_digest(runner=lambda **kw: {"sent": False, "trace": []})
    assert calls == []


def test_user_digests_are_skipped_in_all_mode_and_without_secret(monkeypatch):
    calls = []
    monkeypatch.setattr(scheduler, "send_user_digests", lambda: calls.append(1))
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    scheduler.run_digest(runner=lambda **kw: {"sent": True, "trace": []}, include_all=True)
    monkeypatch.setattr(settings, "auth_secret", "")
    scheduler.run_digest(runner=lambda **kw: {"sent": True, "trace": []})
    assert calls == []


def test_user_digest_failure_does_not_break_the_main_digest(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)

    def boom():
        raise RuntimeError("smtp down")

    monkeypatch.setattr(scheduler, "send_user_digests", boom)
    result = scheduler.run_digest(runner=lambda **kw: {"sent": True, "trace": []})
    assert result["sent"] is True


# ---------- main() ----------
@pytest.mark.parametrize(
    "flag,name",
    [
        ("--alerts-now", "run_alerts"),
        ("--videos-now", "run_videos"),
        ("--weekly-now", "run_weekly"),
        ("--user-digests-now", "run_user_digests"),
    ],
)
def test_main_flags_run_a_single_job(monkeypatch, flag, name):
    called = []
    monkeypatch.setattr(sys, "argv", ["scheduler", flag])
    monkeypatch.setattr(scheduler, name, lambda *a, **k: called.append(name))
    scheduler.main()
    assert called == [name]


def test_main_digest_now_passes_the_all_flag(monkeypatch):
    seen = []
    monkeypatch.setattr(scheduler, "run_digest", lambda include_all=False: seen.append(include_all))
    monkeypatch.setattr(sys, "argv", ["scheduler", "--digest-now"])
    scheduler.main()
    monkeypatch.setattr(sys, "argv", ["scheduler", "--digest-now", "--all"])
    scheduler.main()
    assert seen == [False, True]


@pytest.fixture
def fake_scheduler(monkeypatch):
    made = []

    class Fake:
        def __init__(self):
            self.jobs = []
            self.started = False

        def add_job(self, func, trigger, **kwargs):
            self.jobs.append((func, trigger, kwargs))

        def start(self):
            self.started = True
            raise KeyboardInterrupt

    def factory():
        item = Fake()
        made.append(item)
        return item

    monkeypatch.setattr(scheduler, "BlockingScheduler", factory)
    monkeypatch.setattr(sys, "argv", ["scheduler"])
    return made


def test_main_schedules_the_two_core_jobs(monkeypatch, fake_scheduler, capsys):
    monkeypatch.setattr(settings, "weekly_enabled", False)
    monkeypatch.setattr(settings, "auth_secret", "")
    scheduler.main()
    sched = fake_scheduler[0]
    assert len(sched.jobs) == 2 and sched.started is True
    assert "Scheduler band ho gaya." in capsys.readouterr().out


def test_main_adds_weekly_and_user_digest_jobs(monkeypatch, fake_scheduler):
    monkeypatch.setattr(settings, "weekly_enabled", True)
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    scheduler.main()
    assert len(fake_scheduler[0].jobs) == 4


def test_user_digest_job_runs_the_user_digest_runner(monkeypatch, fake_scheduler):
    monkeypatch.setattr(settings, "weekly_enabled", False)
    monkeypatch.setattr(settings, "auth_secret", "t" * 32)
    called = []
    monkeypatch.setattr(scheduler, "run_user_digests", lambda: called.append(1))
    scheduler.main()
    func = fake_scheduler[0].jobs[2][0]
    func()
    assert called == [1]

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def safe_defaults(monkeypatch):
    """Tests me asli embeddings, YouTube/Gemini calls, security keys ya Resend na hon.
    Jis test ko chahiye wo khud set karta hai."""
    monkeypatch.setattr(settings, "use_embeddings", False)
    monkeypatch.setattr(settings, "include_videos", False)
    monkeypatch.setattr(settings, "api_key", "")
    monkeypatch.setattr(settings, "dashboard_password", "")
    monkeypatch.setattr(settings, "resend_api_key", "")


import pytest


@pytest.fixture(autouse=True)
def _no_real_telegram(monkeypatch):
    """Tests must never send real Telegram messages."""
    import app.core.telegram_notifier as tn

    def _blocked(url, payload, timeout=15):
        raise RuntimeError("real Telegram call blocked in tests")

    monkeypatch.setattr(tn, "_default_post", _blocked)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Har test saaf rate-limit hisaab se shuru ho."""
    from app.core.ratelimit import reset_all

    reset_all()
    yield
    reset_all()


@pytest.fixture(autouse=True)
def _no_source_health_writes(monkeypatch):
    """collect_all must not write to the real database during tests."""
    import app.core.source_health as sh

    def _blocked():
        raise RuntimeError("real database blocked in tests")

    monkeypatch.setattr(sh, "SessionLocal", _blocked)
    monkeypatch.setattr(sh, "init_db", lambda: None)


@pytest.fixture(autouse=True)
def _no_api_key_db(monkeypatch):
    """get_client must not read the real database during tests."""
    import app.core.api_keys as ak

    def _blocked():
        raise RuntimeError("real database blocked in tests")

    monkeypatch.setattr(ak, "SessionLocal", _blocked)
    monkeypatch.setattr(ak, "init_db", lambda: None)
    ak._exhausted.clear()

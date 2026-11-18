from app.core.config import Settings


def test_digest_web_check_default_off(monkeypatch):
    monkeypatch.delenv("DIGEST_WEB_CHECK", raising=False)
    assert Settings(_env_file=None).digest_web_check is False


def test_digest_web_check_reads_env(monkeypatch):
    monkeypatch.setenv("DIGEST_WEB_CHECK", "true")
    assert Settings(_env_file=None).digest_web_check is True

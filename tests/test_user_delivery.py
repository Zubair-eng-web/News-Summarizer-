import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents import user_digest
from app.core import models, users  # noqa: F401
from app.core.database import Base

STORIES = [
    {"title": "Budget talks", "summary": "", "priority": "Medium", "sources": []},
    {"title": "Quake", "summary": "", "priority": "Critical", "sources": []},
]


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def make_user(factory):
    return users.create_user("a@x.com", "password123", factory)["id"]


def test_defaults(factory):
    uid = make_user(factory)
    assert users.get_delivery_settings(uid, factory) == {
        "digest_enabled": False,
        "telegram_chat_id": "",
        "digest_hour": None,
    }


def test_update_roundtrip_and_clear_hour(factory):
    uid = make_user(factory)
    got = users.update_delivery_settings(
        uid, digest_enabled=True, telegram_chat_id=" 12345 ", digest_hour="18", session_factory=factory
    )
    assert got == {"digest_enabled": True, "telegram_chat_id": "12345", "digest_hour": 18}
    got = users.update_delivery_settings(uid, digest_hour=None, session_factory=factory)
    assert got == {"digest_enabled": True, "telegram_chat_id": "12345", "digest_hour": None}


def test_invalid_values_rejected(factory):
    uid = make_user(factory)
    with pytest.raises(ValueError):
        users.update_delivery_settings(uid, telegram_chat_id="abc def", session_factory=factory)
    with pytest.raises(ValueError):
        users.update_delivery_settings(uid, digest_hour=24, session_factory=factory)
    with pytest.raises(ValueError):
        users.update_delivery_settings(uid, digest_hour="x", session_factory=factory)


def test_unknown_user_returns_none(factory):
    assert users.update_delivery_settings(999, digest_enabled=True, session_factory=factory) is None


def test_recipients_carry_delivery_fields(factory):
    uid = make_user(factory)
    users.update_delivery_settings(
        uid, digest_enabled=True, telegram_chat_id="555", digest_hour=7, session_factory=factory
    )
    rows = users.list_digest_recipients(factory)
    assert rows[0]["telegram_chat_id"] == "555" and rows[0]["digest_hour"] == 7


def run_digest(recipients, hour, telegram=None):
    sent = []
    result = user_digest.send_user_digests(
        recipients=recipients,
        stories=STORIES,
        sender=lambda items, email: sent.append(email),
        already_sent=lambda uid, day: False,
        mark_sent=lambda uid, day: None,
        telegram=telegram,
        now_hour=hour,
        today="2026-11-17",
    )
    return result, sent


def test_digest_waits_for_users_hour():
    person = {"id": 1, "email": "a@x.com", "interests": [], "digest_hour": 18}
    result, sent = run_digest([person], hour=10)
    assert result == {"sent": 0, "skipped": 1, "failed": 0} and sent == []
    result, sent = run_digest([person], hour=18)
    assert result == {"sent": 1, "skipped": 0, "failed": 0} and sent == ["a@x.com"]


def test_telegram_gets_short_list():
    calls = []
    person = {"id": 1, "email": "a@x.com", "interests": [], "telegram_chat_id": "555"}
    result, _ = run_digest([person], hour=9, telegram=lambda chat, text: calls.append((chat, text)))
    assert result["sent"] == 1
    assert calls[0][0] == "555" and "[Critical] Quake" in calls[0][1]


def test_telegram_failure_does_not_break_digest():
    def boom(chat, text):
        raise RuntimeError("telegram down")

    person = {"id": 1, "email": "a@x.com", "interests": [], "telegram_chat_id": "555"}
    result, sent = run_digest([person], hour=9, telegram=boom)
    assert result == {"sent": 1, "skipped": 0, "failed": 0} and sent == ["a@x.com"]


def test_no_telegram_call_without_chat_id():
    calls = []
    person = {"id": 1, "email": "a@x.com", "interests": []}
    run_digest([person], hour=9, telegram=lambda chat, text: calls.append(chat))
    assert calls == []

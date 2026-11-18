import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import interests, models, storage  # noqa: F401
from app.core.config import settings
from app.core.database import Base


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 't.db').as_posix()}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        storage, "SessionLocal", sessionmaker(bind=engine, autoflush=False, autocommit=False)
    )
    monkeypatch.setattr(storage, "init_db", lambda: None)
    return engine


def test_setting_roundtrip_and_overwrite(temp_db):
    assert storage.get_setting("k") is None
    storage.set_setting("k", "one")
    assert storage.get_setting("k") == "one"
    storage.set_setting("k", "two")
    assert storage.get_setting("k") == "two"


def test_save_interests_cleans_input(temp_db):
    saved = interests.save_interests("Cricket, AI, cricket ;  Pakistan\n")
    assert saved == ["cricket", "ai", "pakistan"]
    assert storage.get_setting(interests.INTERESTS_KEY) == "cricket, ai, pakistan"


def test_save_interests_is_capped(temp_db):
    many = ",".join(f"kw{i}" for i in range(100))
    assert len(interests.save_interests(many)) == interests.MAX_INTERESTS


def test_stored_interests_override_env(temp_db, monkeypatch):
    monkeypatch.setattr(settings, "interests", "weather")
    interests.save_interests("cricket")
    assert interests.get_interests() == ["cricket"]


def test_empty_stored_value_disables_personalization(temp_db, monkeypatch):
    monkeypatch.setattr(settings, "interests", "weather")
    interests.save_interests("")
    assert interests.get_interests() == []


def test_falls_back_to_env_when_nothing_stored(temp_db, monkeypatch):
    monkeypatch.setattr(settings, "interests", "weather, ai")
    assert interests.get_interests() == ["weather", "ai"]
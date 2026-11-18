from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import models  # noqa: F401
from app.core import storage
from app.core.database import Base
from app.core.models import StoryDB
from app.core.story import Story
from scripts import dedupe_stories


@pytest.fixture
def factory(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    make = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(storage, "SessionLocal", make)
    monkeypatch.setattr(storage, "init_db", lambda: None)
    return make


def story(title="Rwanda hubs", link="https://g/1"):
    return Story(title=title, summary="s", sources=[("Guardian", link)])


def count(factory):
    with factory() as s:
        return s.query(StoryDB).count()


def test_same_story_in_second_digest_is_skipped(factory):
    storage.save_stories([story()])
    storage.save_stories([story()])
    assert count(factory) == 1


def test_different_stories_are_both_saved(factory):
    storage.save_stories([story("A", "https://g/1"), story("B", "https://g/2")])
    assert count(factory) == 2


def test_same_story_twice_in_one_batch_saved_once(factory):
    storage.save_stories([story(), story()])
    assert count(factory) == 1


def test_old_story_can_be_saved_again(factory):
    storage.save_stories([story()])
    with factory() as s:
        row = s.query(StoryDB).first()
        row.created_at = datetime.utcnow() - timedelta(days=30)
        s.commit()
    storage.save_stories([story()])
    assert count(factory) == 2


def test_cleanup_finds_older_duplicates(factory):
    with factory() as s:
        for title in ("one", "one again", "two"):
            link = "https://g/2" if title == "two" else "https://g/1"
            s.add(StoryDB(title=title, summary="", sources_json=f'[["G", "{link}"]]'))
        s.commit()
        dupes = dedupe_stories.find_duplicates(s)
        assert [d.title for d in dupes] == ["one again"]
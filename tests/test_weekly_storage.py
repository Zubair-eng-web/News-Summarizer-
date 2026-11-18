from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import models  # noqa: F401
from app.core import storage
from app.core.database import Base
from app.core.models import StoryDB, VideoDB

START = datetime(2026, 11, 1)
END = datetime(2026, 11, 8)


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(storage, "SessionLocal", factory)
    monkeypatch.setattr(storage, "init_db", lambda: None)
    yield factory
    engine.dispose()


def test_stories_between_is_half_open_and_newest_first(temp_db):
    with temp_db() as s:
        for title, when in [
            ("before", datetime(2026, 10, 31, 23, 59)),
            ("at start", datetime(2026, 11, 1, 0, 0)),
            ("mid", datetime(2026, 11, 5, 10, 0)),
            ("at end", datetime(2026, 11, 8, 0, 0)),
        ]:
            s.add(
                StoryDB(
                    title=title,
                    summary="s",
                    priority="High",
                    sentiment="neutral",
                    credibility="Single source",
                    sources_json='[["BBC", "http://x/1"]]',
                    created_at=when,
                )
            )
        s.commit()
    result = storage.get_stories_between(START, END)
    assert [r["title"] for r in result] == ["mid", "at start"]
    assert result[0]["sources"] == [{"source": "BBC", "link": "http://x/1"}]


def test_videos_between_uses_summary_creation_time(temp_db):
    with temp_db() as s:
        for video_id, when in [("old", datetime(2026, 10, 20)), ("new", datetime(2026, 11, 3))]:
            s.add(
                VideoDB(
                    video_id=video_id,
                    title=video_id,
                    link=f"https://youtu.be/{video_id}",
                    channel="C",
                    summary="S",
                    key_points_json='["a"]',
                    takeaway="t",
                    has_transcript=True,
                    created_at=when,
                )
            )
        s.commit()
    result = storage.get_videos_between(START, END)
    assert [v["video_id"] for v in result] == ["new"]
    assert result[0]["key_points"] == ["a"]
    assert result[0]["has_transcript"] is True

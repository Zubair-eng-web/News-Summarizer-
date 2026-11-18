from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import models  # noqa: F401
from app.core import storage
from app.core.database import Base
from app.core.video import VideoSummary


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(storage, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(storage, "init_db", lambda: None)
    yield
    engine.dispose()


def summary(video_id, hour=10, points=None):
    return VideoSummary(
        video_id=video_id,
        title=f"Title {video_id}",
        link=f"https://youtu.be/{video_id}",
        channel="BBC News",
        published=datetime(2026, 11, 5, hour),
        summary="Summary.",
        key_points=points or ["a", "b"],
        takeaway="Takeaway.",
        has_transcript=True,
    )


def test_save_and_get_recent_videos(temp_db):
    storage.save_videos([summary("v1")])
    result = storage.get_recent_videos()
    assert len(result) == 1
    assert result[0]["key_points"] == ["a", "b"]
    assert result[0]["has_transcript"] is True
    assert result[0]["published"] == "2026-11-05T10:00:00"
    assert result[0]["takeaway"] == "Takeaway."


def test_known_video_ids(temp_db):
    assert storage.get_known_video_ids() == set()
    storage.save_videos([summary("v1"), summary("v2")])
    assert storage.get_known_video_ids() == {"v1", "v2"}


def test_saving_same_video_twice_does_not_duplicate(temp_db):
    storage.save_videos([summary("v1")])
    storage.save_videos([summary("v1")])
    assert len(storage.get_recent_videos()) == 1


def test_recent_videos_newest_first_and_limit(temp_db):
    storage.save_videos([summary("old", hour=8), summary("new", hour=12), summary("mid", hour=10)])
    assert [v["video_id"] for v in storage.get_recent_videos()] == ["new", "mid", "old"]
    assert len(storage.get_recent_videos(limit=2)) == 2

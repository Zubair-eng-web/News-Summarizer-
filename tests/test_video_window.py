from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import models  # noqa: F401
from app.core import storage
from app.core.database import Base
from app.core.models import VideoDB
from app.core.video import VideoSummary


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


def summary(video_id):
    return VideoSummary(
        video_id=video_id,
        title=video_id,
        link=f"https://youtu.be/{video_id}",
        channel="C",
        published=datetime(2026, 11, 5, 10),
        summary="S",
    )


def test_hours_filter_uses_summary_creation_time(temp_db):
    storage.save_videos([summary("new"), summary("old")])
    with temp_db() as session:
        row = session.query(VideoDB).filter(VideoDB.video_id == "old").one()
        row.created_at = datetime.utcnow() - timedelta(hours=48)
        session.commit()
    assert [v["video_id"] for v in storage.get_recent_videos(hours=24)] == ["new"]
    assert len(storage.get_recent_videos()) == 2

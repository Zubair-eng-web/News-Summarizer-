from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import models  # noqa: F401
from app.core import search_store
from app.core.database import Base
from app.core.models import ArticleDB


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(search_store, "SessionLocal", factory)
    monkeypatch.setattr(search_store, "init_db", lambda: None)
    yield factory
    engine.dispose()


def test_articles_with_summary_newest_first(temp_db):
    now = datetime.utcnow()
    with temp_db() as s:
        s.add(ArticleDB(title="Old", link="http://x/old", summary="old summary", source="BBC",
                        collected_at=now - timedelta(hours=5)))
        s.add(ArticleDB(title="New", link="http://x/new", summary="new summary", source="Dawn",
                        collected_at=now))
        s.commit()
    rows = search_store.get_articles_with_summary(limit=10)
    assert [r["title"] for r in rows] == ["New", "Old"]
    assert rows[0]["summary"] == "new summary"
    assert len(search_store.get_articles_with_summary(limit=1)) == 1

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors.rss import Article
from app.core import models  # noqa: F401
from app.core import storage
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
    monkeypatch.setattr(storage, "SessionLocal", factory)
    monkeypatch.setattr(storage, "init_db", lambda: None)
    yield factory
    engine.dispose()


def test_long_title_and_source_are_truncated_for_postgres(temp_db):
    storage.save_new_articles(
        [Article(title="T" * 600, link="http://x/1", summary="s", source="S" * 150)]
    )
    with temp_db() as session:
        row = session.query(ArticleDB).one()
    assert len(row.title) == 500
    assert len(row.source) == 100

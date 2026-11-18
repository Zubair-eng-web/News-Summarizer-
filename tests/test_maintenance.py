import sqlite3
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.maintenance import backup_sqlite, cleanup_old_data
from app.core.models import ArticleDB, DigestedDB, EmbeddingDB


def make_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)


def test_cleanup_removes_only_old_rows():
    factory = make_factory()
    now = datetime(2026, 11, 17)
    old, new = now - timedelta(days=100), now - timedelta(days=5)
    with factory() as db:
        db.add_all(
            [
                ArticleDB(title="old", link="https://o", source="S", collected_at=old),
                ArticleDB(title="new", link="https://n", source="S", collected_at=new),
                DigestedDB(link="https://o", digested_at=old),
                DigestedDB(link="https://n", digested_at=new),
                EmbeddingDB(text_hash="a", model="m", vector=b"x", created_at=old),
                EmbeddingDB(text_hash="b", model="m", vector=b"x", created_at=new),
            ]
        )
        db.commit()
    counts = cleanup_old_data(days=90, session_factory=factory, now=now)
    assert counts == {"articles": 1, "digested": 1, "embeddings": 1}
    with factory() as db:
        assert [a.title for a in db.query(ArticleDB)] == ["new"]
        assert db.query(DigestedDB).count() == 1
        assert db.query(EmbeddingDB).count() == 1


def test_cleanup_disabled_when_days_is_zero():
    assert cleanup_old_data(days=0) == {"articles": 0, "digested": 0, "embeddings": 0}


def make_db(path):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (42)")
    conn.commit()
    conn.close()


def test_backup_copies_data(tmp_path):
    source = tmp_path / "app.db"
    make_db(source)
    dest = backup_sqlite(
        f"sqlite:///{source.as_posix()}", tmp_path / "bk", now=datetime(2026, 1, 1, 10, 0, 0)
    )
    conn = sqlite3.connect(str(dest))
    try:
        assert conn.execute("SELECT x FROM t").fetchone() == (42,)
    finally:
        conn.close()


def test_backup_keeps_only_newest(tmp_path):
    source = tmp_path / "app.db"
    make_db(source)
    url = f"sqlite:///{source.as_posix()}"
    for second in range(4):
        backup_sqlite(url, tmp_path / "bk", keep=2, now=datetime(2026, 1, 1, 10, 0, second))
    names = sorted(p.name for p in (tmp_path / "bk").glob("*.db"))
    assert names == ["app-20260101-100002.db", "app-20260101-100003.db"]


def test_backup_rejects_non_sqlite_and_missing_file(tmp_path):
    with pytest.raises(ValueError):
        backup_sqlite("postgresql+psycopg://u:p@host/db", tmp_path)
    with pytest.raises(FileNotFoundError):
        backup_sqlite(f"sqlite:///{(tmp_path / 'nope.db').as_posix()}", tmp_path)
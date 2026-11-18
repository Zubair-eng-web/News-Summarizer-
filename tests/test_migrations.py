import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.core import models  # noqa: F401
from app.core.database import Base
from app.core.migrate import upgrade_database

import pathlib

HEAD = sorted(
    f.name[:4]
    for f in (pathlib.Path(__file__).resolve().parent.parent / "migrations" / "versions").glob("0*.py")
)[-1]


@pytest.fixture
def url(tmp_path):
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


def scalar(url, sql):
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).scalar()
    finally:
        engine.dispose()


def test_fresh_database_matches_models(url):
    upgrade_database(url)
    assert scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    finally:
        engine.dispose()
    assert diffs == []


def test_legacy_database_is_stamped_and_data_kept(url):
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app_settings (key, value, updated_at) "
                "VALUES ('interests', 'ai', '2026-01-01 00:00:00')"
            )
        )
    engine.dispose()

    upgrade_database(url)
    assert scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert scalar(url, "SELECT value FROM app_settings WHERE key = 'interests'") == "ai"


def test_upgrade_is_idempotent(url):
    upgrade_database(url)
    upgrade_database(url)
    assert scalar(url, "SELECT COUNT(*) FROM alembic_version") == 1
from alembic import command
from sqlalchemy import create_engine, inspect

from app.core.migrate import make_config, upgrade_database


def tables(url):
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_from_baseline_adds_user_sources(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    command.upgrade(make_config(url), "0001")
    assert "user_sources" not in tables(url)
    upgrade_database(url)
    assert "user_sources" in tables(url)
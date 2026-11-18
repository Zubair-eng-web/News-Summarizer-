from alembic import command
from sqlalchemy import create_engine, inspect, text

from app.core.migrate import make_config, upgrade_database


def test_0003_adds_claims_column_and_keeps_rows(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    command.upgrade(make_config(url), "0002")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO stories (title, summary, priority, sentiment, credibility, "
                "sources_json, created_at) VALUES ('T', 'S', 'High', 'neutral', "
                "'Single source', '[]', '2026-01-01 00:00:00')"
            )
        )
    engine.dispose()

    upgrade_database(url)
    engine = create_engine(url)
    try:
        columns = {c["name"] for c in inspect(engine).get_columns("stories")}
        with engine.connect() as conn:
            value = conn.execute(text("SELECT claims_json FROM stories")).scalar()
            title = conn.execute(text("SELECT title FROM stories")).scalar()
    finally:
        engine.dispose()
    assert "claims_json" in columns
    assert value == "[]" and title == "T"
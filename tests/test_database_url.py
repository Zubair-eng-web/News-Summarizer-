from app.core.database import engine_kwargs, normalize_database_url


def test_render_style_urls_get_psycopg_driver():
    assert normalize_database_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert normalize_database_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"


def test_other_urls_are_unchanged():
    assert normalize_database_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url("sqlite:///briefing.db") == "sqlite:///briefing.db"
    assert normalize_database_url("  sqlite:///x.db  ") == "sqlite:///x.db"


def test_sqlite_engine_allows_threads():
    assert engine_kwargs("sqlite:///x.db") == {"connect_args": {"check_same_thread": False}}


def test_postgres_engine_checks_connections():
    assert engine_kwargs("postgresql+psycopg://u:p@h/db") == {"pool_pre_ping": True}

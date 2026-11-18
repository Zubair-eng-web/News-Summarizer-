"""Database migrations (Alembic).

Naya database: seedha upgrade. Purana database (jo create_all se bana tha, jisme
alembic_version nahi hai): pehle missing tables banate hain, baseline par stamp karte hain,
phir upgrade. Is se existing data ko koi nuksan nahi hota.

Chalane ka tareeqa: python -m app.core.migrate
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.database import DATABASE_URL, Base

BASELINE = "0001"
ROOT = Path(__file__).resolve().parents[2]


def make_config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def upgrade_database(url: str | None = None) -> None:
    url = url or DATABASE_URL
    cfg = make_config(url)
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        if "alembic_version" not in tables and "articles" in tables:
            from app.core import models  # noqa: F401

            Base.metadata.create_all(bind=engine)
            command.stamp(cfg, BASELINE)
    finally:
        engine.dispose()
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    upgrade_database()
    print("Database is up to date")
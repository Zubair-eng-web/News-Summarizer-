"""Alembic environment: URL aur models app ke apne settings se aate hain."""
from alembic import context
from sqlalchemy import create_engine, pool

from app.core import models  # noqa: F401
from app.core.database import DATABASE_URL, Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or DATABASE_URL
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline (--sql) mode is project me supported nahi hai")
run_migrations_online()
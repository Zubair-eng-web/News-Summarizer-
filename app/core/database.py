from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """Render 'postgres://' deta hai, SQLAlchemy ko 'postgresql+psycopg://' chahiye."""
    url = (url or "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}  # toote hue connections khud theek ho jate hain


DATABASE_URL = normalize_database_url(settings.database_url)

engine = create_engine(DATABASE_URL, **engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


_migrated = False


def init_db():
    """Tables banata hai aur (process me ek baar) migrations chalata hai."""
    global _migrated
    from app.core import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if not _migrated:
        from app.core.migrate import upgrade_database

        upgrade_database()
        _migrated = True

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import models  # noqa: F401  (tables register karne ke liye)
from app.core.database import Base
from app.core.models import ArticleDB, StoryDB, VideoDB
from app.core.story import PRIORITIES
from scripts import seed_demo


def _factory():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_seed_fills_empty_database():
    factory = _factory()
    result = seed_demo.seed(factory)
    assert result["seeded"] is True
    with factory() as s:
        assert s.query(StoryDB).count() == len(seed_demo.STORIES)
        assert s.query(ArticleDB).count() == len(seed_demo.STORIES)
        assert s.query(VideoDB).count() == len(seed_demo.VIDEOS)


def test_seed_is_idempotent():
    factory = _factory()
    seed_demo.seed(factory)
    assert seed_demo.seed(factory)["seeded"] is False
    with factory() as s:
        assert s.query(StoryDB).count() == len(seed_demo.STORIES)


def test_force_replaces_without_duplicates():
    factory = _factory()
    seed_demo.seed(factory)
    assert seed_demo.seed(factory, force=True)["seeded"] is True
    with factory() as s:
        assert s.query(StoryDB).count() == len(seed_demo.STORIES)
        assert s.query(VideoDB).count() == len(seed_demo.VIDEOS)


def test_demo_stories_use_valid_priorities():
    assert {s["priority"] for s in seed_demo.STORIES} <= set(PRIORITIES)


def test_render_demo_yaml_is_read_only_and_docker_free():
    text = Path("render-demo.yaml").read_text(encoding="utf-8")
    assert 'DEMO_MODE' in text and '"true"' in text
    assert "docker" not in text.lower()
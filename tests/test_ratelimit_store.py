import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import ratelimit, ratelimit_store


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "r.db"
    engines = []

    def factory():
        engine = create_engine(f"sqlite:///{path}")
        engines.append(engine)
        return sessionmaker(bind=engine)

    factory.make = factory
    yield factory
    for e in engines:
        e.dispose()


def test_blocks_after_limit_and_recovers(db_path):
    f = db_path.make()
    t = [1000.0]
    clock = lambda: t[0]  # noqa: E731
    assert ratelimit_store.hit("k", 2, 60, f, clock) == 0
    assert ratelimit_store.hit("k", 2, 60, f, clock) == 0
    assert ratelimit_store.hit("k", 2, 60, f, clock) > 0
    t[0] = 1061.0
    assert ratelimit_store.hit("k", 2, 60, f, clock) == 0


def test_survives_restart(db_path):
    clock = lambda: 5000.0  # noqa: E731
    ratelimit_store.hit("k", 1, 60, db_path.make(), clock)
    assert ratelimit_store.hit("k", 1, 60, db_path.make(), clock) > 0


def test_keys_are_independent(db_path):
    f = db_path.make()
    clock = lambda: 1.0  # noqa: E731
    assert ratelimit_store.hit("a", 1, 60, f, clock) == 0
    assert ratelimit_store.hit("b", 1, 60, f, clock) == 0


def test_hit_falls_back_to_memory(monkeypatch):
    ratelimit.reset_all()
    monkeypatch.setenv("RATE_LIMIT_PERSISTENT", "true")

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(ratelimit_store, "hit", boom)
    assert ratelimit.hit("x", 1, 60) == 0
    assert ratelimit.hit("x", 1, 60) > 0
    ratelimit.reset_all()

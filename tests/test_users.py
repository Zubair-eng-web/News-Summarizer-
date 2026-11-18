import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import models  # noqa: F401
from app.core import users
from app.core.database import Base


@pytest.fixture
def factory(monkeypatch):
    monkeypatch.setattr(users, "ITERATIONS", 1000)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(users, "SessionLocal", session_factory)
    return session_factory


def test_password_hash_roundtrip():
    stored = users.hash_password("correct horse")
    assert users.verify_password("correct horse", stored)
    assert not users.verify_password("wrong", stored)
    assert not users.verify_password("x", "not-a-hash")


def test_hashes_are_salted():
    assert users.hash_password("same") != users.hash_password("same")


def test_create_and_duplicate(factory):
    user = users.create_user("  Ali@Example.com ", "password123")
    assert user["email"] == "ali@example.com"
    assert user["interests"] == []
    with pytest.raises(users.UserExistsError):
        users.create_user("ali@example.com", "another-pass")


def test_authenticate(factory):
    users.create_user("ali@example.com", "password123")
    assert users.authenticate("ALI@example.com", "password123")["email"] == "ali@example.com"
    assert users.authenticate("ali@example.com", "nope-nope") is None
    assert users.authenticate("ghost@example.com", "password123") is None


def test_interests_clean_and_per_user(factory):
    a = users.create_user("a@example.com", "password123")
    b = users.create_user("b@example.com", "password123")
    assert users.set_user_interests(a["id"], "AI, cricket, ai; Pakistan") == [
        "ai", "cricket", "pakistan",
    ]
    assert users.get_user(a["id"])["interests"] == ["ai", "cricket", "pakistan"]
    assert users.get_user(b["id"])["interests"] == []
    assert users.set_user_interests(9999, "ai") is None


def test_email_validation():
    assert users.is_valid_email("a@b.co")
    assert not users.is_valid_email("no-at-sign")
    assert not users.is_valid_email("a@b")
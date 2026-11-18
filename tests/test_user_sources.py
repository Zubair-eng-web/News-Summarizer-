import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import models  # noqa: F401
from app.core import user_sources as us
from app.core.database import Base

CID = "UC" + "a" * 22


def public(host, port):
    return [(0, 0, 0, "", ("93.184.216.34", port))]


def private(host, port):
    return [(0, 0, 0, "", ("10.0.0.5", port))]


def loopback(host, port):
    return [(0, 0, 0, "", ("127.0.0.1", port))]


def mapped(host, port):
    return [(0, 0, 0, "", ("::ffff:10.0.0.5", port, 0, 0))]


def mixed(host, port):
    return public(host, port) + private(host, port)


def fails(host, port):
    raise OSError("dns down")


@pytest.fixture
def factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)


def test_is_public_url_rules():
    assert us.is_public_url("https://example.com/rss", public)
    assert us.is_public_url("http://example.com:80/rss", public)
    assert not us.is_public_url("ftp://example.com/rss", public)
    assert not us.is_public_url("https://user:pw@example.com/rss", public)
    assert not us.is_public_url("https://example.com:8080/rss", public)
    assert not us.is_public_url("https://internal.test/rss", private)
    assert not us.is_public_url("http://127.0.0.1/rss", loopback)
    assert not us.is_public_url("https://mapped.test/rss", mapped)
    assert not us.is_public_url("https://mixed.test/rss", mixed)
    assert not us.is_public_url("https://x.test/rss", fails)
    assert not us.is_public_url("not a url", public)


def test_normalize_rss():
    kind, url, name = us.normalize_source(
        "rss", " https://example.com/rss ", "  My <Feed> [x] ", resolver=public
    )
    assert (kind, url, name) == ("rss", "https://example.com/rss", "My Feed x")
    with pytest.raises(us.SourceError):
        us.normalize_source("rss", "https://x.test/rss", "N", resolver=private)
    with pytest.raises(us.SourceError):
        us.normalize_source("rss", "https://example.com/rss", "   ", resolver=public)
    with pytest.raises(us.SourceError):
        us.normalize_source("podcast", "https://example.com/rss", "N", resolver=public)


def test_normalize_youtube():
    assert us.normalize_source("youtube", CID, "")[1:] == (CID, CID)
    link = f"https://www.youtube.com/channel/{CID}/videos"
    assert us.normalize_source("youtube", link, "BBC")[1:] == (CID, "BBC")
    with pytest.raises(us.SourceError):
        us.normalize_source("youtube", "@handle", "x")


def test_add_list_delete_and_ownership(factory):
    a = us.add_source(1, "rss", "https://example.com/rss", "One", factory, public)
    assert a["name"] == "One" and a["kind"] == "rss"
    assert [s["id"] for s in us.list_sources(1, factory)] == [a["id"]]
    assert us.list_sources(2, factory) == []
    assert us.delete_source(2, a["id"], factory) is False
    assert us.delete_source(1, a["id"], factory) is True
    assert us.list_sources(1, factory) == []


def test_limits_and_duplicates(factory, monkeypatch):
    monkeypatch.setattr(us, "MAX_PER_USER", 2)
    us.add_source(1, "rss", "https://a.example/rss", "A", factory, public)
    with pytest.raises(us.SourceExistsError):
        us.add_source(1, "rss", "https://a.example/rss", "A again", factory, public)
    us.add_source(1, "rss", "https://b.example/rss", "B", factory, public)
    with pytest.raises(us.SourceLimitError):
        us.add_source(1, "rss", "https://c.example/rss", "C", factory, public)
    assert us.add_source(2, "rss", "https://a.example/rss", "A", factory, public)["id"]


def test_loaders(factory):
    us.add_source(1, "rss", "https://a.example/rss", "A", factory, public)
    us.add_source(2, "rss", "https://a.example/rss", "B", factory, public)
    us.add_source(2, "rss", "https://b.example/rss", "A", factory, public)
    us.add_source(1, "youtube", CID, "Chan", factory)
    feeds = us.load_extra_feeds(factory, public)
    assert len(feeds) == 2
    assert feeds["A (custom)"] == "https://a.example/rss"
    assert set(feeds.values()) == {"https://a.example/rss", "https://b.example/rss"}
    assert us.load_extra_feeds(factory, private) == {}
    assert us.load_extra_channels(factory) == {"Chan (custom)": CID}
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors.rss import Article
from app.core import models  # noqa: F401
from app.core import storage
from app.core.database import Base
from app.core.models import ArticleDB
from app.graph.briefing import build_briefing_graph


class FakeModels:
    def generate_content(self, **kwargs):
        if "news editor" in kwargs["config"].system_instruction:
            n = kwargs["contents"].count("\n") + 1
            data = [{"id": i, "priority": "High", "sentiment": "neutral"} for i in range(1, n + 1)]
            return SimpleNamespace(text=json.dumps(data))
        return SimpleNamespace(text="Fake summary.")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(storage, "SessionLocal", factory)
    monkeypatch.setattr(storage, "init_db", lambda: None)
    return factory


def add_article(factory, link, hours_ago=0):
    with factory() as s:
        s.add(
            ArticleDB(
                title=f"T {link}",
                link=link,
                summary="s",
                source="BBC",
                collected_at=datetime.utcnow() - timedelta(hours=hours_ago),
            )
        )
        s.commit()


def article(link):
    return Article(title=f"T {link}", link=link, summary="s", source="BBC")


def test_undigested_returns_unmarked_articles(temp_db):
    add_article(temp_db, "http://x/1")
    add_article(temp_db, "http://x/2")
    assert len(storage.get_undigested_articles()) == 2


def test_mark_digested_hides_articles(temp_db):
    add_article(temp_db, "http://x/1")
    add_article(temp_db, "http://x/2")
    storage.mark_digested([article("http://x/1")])
    left = storage.get_undigested_articles()
    assert [a.link for a in left] == ["http://x/2"]


def test_old_articles_outside_window_ignored(temp_db):
    add_article(temp_db, "http://x/old", hours_ago=100)
    add_article(temp_db, "http://x/new", hours_ago=1)
    assert [a.link for a in storage.get_undigested_articles(hours=36)] == ["http://x/new"]


def test_mark_digested_twice_is_safe(temp_db):
    add_article(temp_db, "http://x/1")
    storage.mark_digested([article("http://x/1")])
    storage.mark_digested([article("http://x/1")])
    assert storage.get_undigested_articles() == []


def test_graph_uses_selector_and_marks_after_email():
    arts = [Article(title="Ronaldo retires from Portugal team", link="http://x/r", summary="", source="BBC")]
    sent, marked = [], []
    graph = build_briefing_graph(
        client=FakeClient(),
        collector=lambda n: arts,
        saver=lambda a: [],  # DB ke hisaab se koi naya article nahi
        selector=lambda: arts,  # lekin digest me bheji nahi gayi article maujood hai
        sender=sent.append,
        digest_marker=marked.append,
        alert_sender=lambda s: None,
        alert_filter=lambda s: s,
        alert_marker=lambda s: None,
        delay=0,
    )
    result = graph.invoke({"trace": []})
    assert len(sent) == 1
    assert marked == [arts]
    assert result["sent"] is True

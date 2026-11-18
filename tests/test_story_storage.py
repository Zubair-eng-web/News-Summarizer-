import json
import time
from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.collectors.rss import Article
from app.core import models  # noqa: F401
from app.core import storage
from app.core.database import Base
from app.core.models import AlertDB, ArticleDB
from app.core.story import Story
from app.graph.briefing import build_briefing_graph


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(storage, "SessionLocal", factory)
    monkeypatch.setattr(storage, "init_db", lambda: None)
    yield factory
    engine.dispose()


def story(title, link, priority="High"):
    return Story(
        title=title,
        summary="Summary.",
        sources=[("BBC", link)],
        priority=priority,
        sentiment="negative",
        credibility="Single source",
    )


def test_save_and_get_recent_stories(temp_db):
    storage.save_stories([story("A", "http://x/a", "Critical"), story("B", "http://x/b", "Low")])
    result = storage.get_recent_stories()
    assert [s["title"] for s in result] == ["A", "B"]  # rank ka order bacha rehta hai
    assert result[0]["sources"] == [{"source": "BBC", "link": "http://x/a"}]
    assert result[0]["created_at"] is not None


def test_priority_filter(temp_db):
    storage.save_stories([story("A", "http://x/a", "Critical"), story("B", "http://x/b", "Low")])
    assert [s["title"] for s in storage.get_recent_stories(priority="Low")] == ["B"]


def test_limit(temp_db):
    storage.save_stories([story("A", "http://x/a"), story("B", "http://x/b")])
    assert len(storage.get_recent_stories(limit=1)) == 1


def test_newest_digest_comes_first(temp_db):
    storage.save_stories([story("Old", "http://x/old")])
    time.sleep(0.05)
    storage.save_stories([story("New", "http://x/new")])
    assert [s["title"] for s in storage.get_recent_stories()] == ["New", "Old"]


def test_get_recent_articles(temp_db):
    with temp_db() as s:
        s.add(ArticleDB(title="T", link="http://x/1", summary="s", source="BBC",
                        collected_at=datetime.utcnow()))
        s.commit()
    result = storage.get_recent_articles()
    assert len(result) == 1 and result[0]["source"] == "BBC"


def test_stats(temp_db):
    storage.save_stories([story("A", "http://x/a", "Critical"), story("B", "http://x/b", "Low")])
    with temp_db() as s:
        s.add(AlertDB(story_key="k", title="t"))
        s.commit()
    stats = storage.get_stats()
    assert stats["stories"] == 2
    assert stats["alerts_sent"] == 1
    assert stats["stories_by_priority"]["Critical"] == 1
    assert stats["stories_by_priority"]["Medium"] == 0


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


def test_graph_saves_stories_after_email():
    arts = [Article(title="Ronaldo retires from Portugal team", link="http://x/r",
                    summary="", source="BBC")]
    sent, saved = [], []
    graph = build_briefing_graph(
        client=FakeClient(),
        collector=lambda n: arts,
        saver=lambda a: a,
        sender=sent.append,
        story_saver=saved.append,
        alert_sender=lambda s: None,
        alert_filter=lambda s: s,
        alert_marker=lambda s: None,
        delay=0,
    )
    graph.invoke({"trace": []})
    assert len(sent) == 1
    assert len(saved) == 1 and len(saved[0]) == 1

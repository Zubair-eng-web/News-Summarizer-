from datetime import datetime

from app.core import database, migrate
from app.core.models import StoryDB
from app.core.personalize import personalize_stories
from app.core.storage import _story_to_dict

CLAIMS = '[{"claim": "Toll is 12", "supported_by": ["BBC"], "contradicted_by": ["Dawn"], "status": "disputed"}]'


def row(claims_json):
    return StoryDB(
        id=1,
        title="T",
        summary="S",
        priority="High",
        sentiment="neutral",
        credibility="Single source",
        sources_json="[]",
        claims_json=claims_json,
        created_at=datetime(2026, 1, 1),
    )


def test_claims_are_parsed_into_the_story_dict():
    claims = _story_to_dict(row(CLAIMS))["claims"]
    assert claims[0]["status"] == "disputed" and claims[0]["contradicted_by"] == ["Dawn"]


def test_bad_claims_json_becomes_empty_list():
    for bad in ("not json", '{"a": 1}', "", None):
        assert _story_to_dict(row(bad))["claims"] == []


def test_personalize_keeps_claims():
    stories = [{"title": "Cricket", "summary": "", "priority": "Medium", "sources": [], "claims": [{"claim": "x"}]}]
    assert personalize_stories(stories, ["cricket"])[0]["claims"] == [{"claim": "x"}]


def test_init_db_runs_migrations_only_once(monkeypatch):
    calls = []
    monkeypatch.setattr(migrate, "upgrade_database", lambda *a, **k: calls.append(1))
    monkeypatch.setattr(database, "_migrated", False)
    database.init_db()
    database.init_db()
    assert calls == [1]
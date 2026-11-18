from app.agents.ranker import rank_stories
from app.core.config import settings
from app.core.interests import matches_interests, parse_interests
from app.core.story import Story


def mk(title, priority, sources=1, summary=""):
    return Story(
        title=title,
        summary=summary,
        sources=[("S", f"http://x/{title}/{i}") for i in range(sources)],
        priority=priority,
        sentiment="neutral",
        credibility="Single source",
    )


def titles(stories):
    return [s.title for s in stories]


def test_parse_interests():
    assert parse_interests("Cricket, AI ;Pakistan\n tech ") == ["cricket", "ai", "pakistan", "tech"]
    assert parse_interests("") == []
    assert parse_interests(None) == []


def test_match_word_boundary_and_case():
    assert matches_interests("New AI model released", ["ai"]) == ["ai"]
    assert matches_interests("He said it was fine", ["ai"]) == []
    assert matches_interests("CRICKET final today", ["cricket"]) == ["cricket"]


def test_no_interests_keeps_original_order():
    stories = [mk("low", "Low"), mk("high", "High"), mk("crit", "Critical")]
    assert titles(rank_stories(stories, interests=[])) == ["crit", "high", "low"]


def test_interest_promotes_one_tier_below_real_high():
    stories = [
        mk("Weather update", "Medium", sources=3),
        mk("Cricket final", "Medium", sources=1),
        mk("Budget talks", "High", sources=1),
    ]
    ranked = rank_stories(stories, interests=["cricket"])
    assert titles(ranked) == ["Budget talks", "Cricket final", "Weather update"]


def test_more_matches_rank_first_within_tier():
    stories = [
        mk("Cricket news", "Medium", sources=4),
        mk("Pakistan cricket squad", "Medium", sources=1),
    ]
    ranked = rank_stories(stories, interests=["cricket", "pakistan"])
    assert titles(ranked)[0] == "Pakistan cricket squad"


def test_critical_never_displaced():
    stories = [mk("Cricket final", "Low"), mk("Weather alert", "Critical")]
    assert titles(rank_stories(stories, interests=["cricket"]))[0] == "Weather alert"


def test_default_reads_settings(monkeypatch):
    monkeypatch.setattr("app.core.interests.load_stored_interests", lambda: None)
    monkeypatch.setattr(settings, "interests", "cricket")
    stories = [mk("Weather update", "Medium", sources=3), mk("Cricket final", "Medium")]
    assert titles(rank_stories(stories))[0] == "Cricket final"
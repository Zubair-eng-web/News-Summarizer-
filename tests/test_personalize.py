from app.core.personalize import personalize_stories


def story(title, priority, sources=0):
    return {"title": title, "summary": "", "priority": priority, "sources": [0] * sources}


def titles(items):
    return [s["title"] for s in items]


def test_interest_promotes_one_tier_but_not_above_real_high():
    stories = [
        story("Budget talks", "Medium"),
        story("Cricket final", "Medium"),
        story("Flood", "High"),
        story("Quake", "Critical"),
    ]
    ranked = personalize_stories(stories, ["cricket"])
    assert titles(ranked) == ["Quake", "Flood", "Cricket final", "Budget talks"]
    assert ranked[2]["matched_interests"] == ["cricket"]


def test_no_interests_keeps_priority_order_and_empty_matches():
    stories = [story("A", "Low"), story("B", "High"), story("C", "Medium")]
    ranked = personalize_stories(stories, [])
    assert titles(ranked) == ["B", "C", "A"]
    assert all(s["matched_interests"] == [] for s in ranked)


def test_whole_word_match_and_input_not_mutated():
    stories = [story("He said hello", "Medium"), story("New AI chip", "Medium")]
    ranked = personalize_stories(stories, ["ai"])
    assert titles(ranked)[0] == "New AI chip"
    assert "matched_interests" not in stories[0]
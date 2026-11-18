from app.agents.analyzer import SYSTEM_PROMPT


def test_prompt_keeps_critical_rules():
    assert "Critical ONLY" in SYSTEM_PROMPT
    assert "At most 1 in 5" in SYSTEM_PROMPT


def test_local_civic_news_belongs_to_medium():
    medium = SYSTEM_PROMPT.split("Medium (")[1].split("Low (")[0]
    assert "civic" in medium and "education" in medium


def test_festivals_and_entertainment_stay_low():
    low = SYSTEM_PROMPT.split("Low (")[1]
    assert "festivals" in low and "entertainment" in low
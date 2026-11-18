from app.collectors.rss import Article
from app.core.dedup import group_duplicates, same_event_by_text


def art(title, summary, source):
    return Article(title=title, link=title, summary=summary, source=source)


FLOOD_A = art(
    "Floods displace thousands of people in Sindh",
    "Heavy rain has forced thousands of families to leave their homes in southern Pakistan.",
    "BBC World",
)
FLOOD_B = art(
    "Flood victims in Sindh wait for relief as water levels rise",
    "Thousands of displaced families in Sindh are waiting for food and shelter as rivers keep rising.",
    "Dawn",
)


def test_same_story_with_few_title_words_is_merged():
    assert same_event_by_text(FLOOD_A, FLOOD_B)
    assert len(group_duplicates([FLOOD_A, FLOOD_B])) == 1


def test_same_source_is_never_merged_by_text():
    twin = art(FLOOD_B.title, FLOOD_B.summary, "BBC World")
    assert not same_event_by_text(FLOOD_A, twin)


def test_related_but_different_stories_stay_apart():
    a = art("Pakistan cricket team arrives in Australia for series",
            "The squad will play three Tests and five one-day matches.", "Dawn")
    b = art("Pakistan cricket board names new chairman",
            "The appointment follows months of disagreement over the leadership.", "BBC World")
    assert not same_event_by_text(a, b)
    assert len(group_duplicates([a, b])) == 2
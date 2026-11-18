from app.collectors.rss import Article
from app.core.dedup import group_duplicates, same_event_by_title, title_tokens


def art(title, source, summary=""):
    return Article(title=title, link=f"http://{source}/{abs(hash(title))}", summary=summary, source=source)


BBC = art(
    "Seven dead and more than 100 injured after trains collide in Egypt", "BBC World",
    "Several carriages derailed as a result of the crash.",
)
GUARDIAN = art(
    "Collision of two trains in Egypt kills at least seven", "The Guardian",
    "A train traveling to Fayoum struck the rear of another heading to Aswan.",
)


def test_title_tokens_stem_and_filter():
    assert "colli" in title_tokens("Trains collide") and "colli" in title_tokens("Collision of trains")
    assert "the" not in title_tokens("The big news")


def test_egypt_story_from_two_outlets_merges():
    groups = group_duplicates([BBC, GUARDIAN])
    assert len(groups) == 1
    assert {a.source for a in groups[0]} == {"BBC World", "The Guardian"}


def test_unrelated_stories_stay_separate():
    iran = art("Iran executes three men for armed unrest after January protests", "BBC World")
    israel = art("Eisenkot says Israel in devastating diplomatic crisis", "Dawn")
    assert len(group_duplicates([BBC, iran, israel, GUARDIAN])) == 3


def test_same_outlet_is_not_merged_by_title_rule():
    a = art("Seven dead after trains collide in Egypt", "BBC World")
    b = art("Egypt trains collide, seven dead and injured", "BBC World")
    assert same_event_by_title(a, b) is False


def test_few_shared_words_do_not_merge():
    a = art("Pakistan wins cricket final against India", "Dawn")
    b = art("Pakistan floods displace thousands in Sindh", "BBC World")
    assert same_event_by_title(a, b) is False


def test_empty_input():
    assert group_duplicates([]) == []
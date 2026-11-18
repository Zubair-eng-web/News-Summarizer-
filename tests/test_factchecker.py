from app.agents.email_agent import build_html
from app.agents.factchecker import check_credibility
from app.core.story import Story


def story(sources):
    return Story(title="T", summary="S", sources=sources)


def test_two_different_sources_confirmed():
    s = check_credibility([story([("BBC", "http://a"), ("Dawn", "http://b")])])[0]
    assert s.credibility == "Confirmed by 2 sources"


def test_same_source_twice_is_single():
    s = check_credibility([story([("BBC", "http://a"), ("BBC", "http://b")])])[0]
    assert s.credibility == "Single source"


def test_single_source():
    s = check_credibility([story([("Dawn", "http://a")])])[0]
    assert s.credibility == "Single source"


def test_email_shows_credibility():
    stories = check_credibility([story([("BBC", "http://a"), ("Dawn", "http://b")])])
    assert "Confirmed by 2 sources" in build_html(stories, "d")

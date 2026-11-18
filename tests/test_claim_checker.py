import json

from app.agents.claim_checker import (
    DIFFER_SUFFIX,
    MAX_CREDIBILITY_LEN,
    MAX_STORIES,
    check_claims,
    parse_verdicts,
)
from app.core.story import Story


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeClient:
    def __init__(self, text=None, boom=False):
        self.text, self.boom, self.calls = text, boom, 0
        self.models = self

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.boom:
            raise RuntimeError("api down")
        return FakeResponse(self.text)


def story(title, outlets=("BBC", "Dawn"), credibility="Confirmed by 2 sources"):
    return Story(
        title=title,
        summary="s",
        sources=[(o, f"http://x/{o}") for o in outlets],
        credibility=credibility,
        evidence=[(o, f"{title} per {o}") for o in outlets],
    )


def test_parse_verdicts_handles_fences_and_garbage():
    text = '```json\n[{"id": 1, "verdict": "DIFFERS", "note": "Death toll 5 vs 9"}]\n```'
    assert parse_verdicts(text) == {1: ("differs", "Death toll 5 vs 9")}
    assert parse_verdicts("not json") == {}
    assert parse_verdicts('{"id": 1}') == {}
    assert parse_verdicts('[{"id": 2, "verdict": "weird"}]') == {2: ("unclear", "")}


def test_differs_marks_credibility_and_note():
    s = story("Quake")
    client = FakeClient(json.dumps([{"id": 1, "verdict": "differs", "note": "Toll differs"}]))
    check_claims([s], client)
    assert s.credibility == "Confirmed by 2 sources" + DIFFER_SUFFIX
    assert s.claim_notes == "Toll differs"
    assert len(s.credibility) <= MAX_CREDIBILITY_LEN


def test_consistent_leaves_story_unchanged():
    s = story("Budget")
    check_claims([s], FakeClient(json.dumps([{"id": 1, "verdict": "consistent", "note": ""}])))
    assert s.credibility == "Confirmed by 2 sources"
    assert s.claim_notes == ""


def test_single_source_story_makes_no_call():
    client = FakeClient("[]")
    check_claims([story("Solo", outlets=("BBC",), credibility="Single source")], client)
    assert client.calls == 0


def test_llm_failure_leaves_stories_untouched():
    s = story("Quake")
    check_claims([s], FakeClient(boom=True))
    assert s.credibility == "Confirmed by 2 sources"


def test_bad_json_leaves_stories_untouched():
    s = story("Quake")
    check_claims([s], FakeClient("sorry, cannot help"))
    assert s.credibility == "Confirmed by 2 sources"


def test_only_top_stories_checked_with_one_call():
    stories = [story(f"S{i}") for i in range(MAX_STORIES + 3)]
    client = FakeClient("[]")
    check_claims(stories, client)
    assert client.calls == 1


def test_rerun_does_not_duplicate_suffix():
    s = story("Quake")
    client = FakeClient(json.dumps([{"id": 1, "verdict": "differs", "note": "n"}]))
    check_claims([s], client)
    check_claims([s], client)
    assert s.credibility.count("Details differ") == 1
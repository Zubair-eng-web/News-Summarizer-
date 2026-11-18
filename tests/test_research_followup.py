import json

from app.agents.deep_research import parse_followups, run_research
from app.agents.research import NO_INFO, Doc


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.models = self

    def generate_content(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


def make_docs():
    return [
        Doc("Egypt trains collided",
            "Egypt trains collided. Seven people died when two trains collided near Giza.",
            [("BBC", "http://bbc/egypt")], "story"),
        Doc("Iran executes men",
            "Iran executed three men. Iran executed men over armed unrest.",
            [("Dawn", "http://dawn/iran")], "story"),
    ]


def test_parse_followups_aligns_and_drops_same_or_empty():
    originals = ["alpha beta", "gamma"]
    assert parse_followups('["alpha beta", "delta gamma"]', originals) == ["", "delta gamma"]
    assert parse_followups("not json", originals) == ["", ""]
    assert parse_followups('{"a": 1}', originals) == ["", ""]
    assert parse_followups('```json\n["x y"]\n```', originals) == ["x y", ""]


def test_missing_subquestion_is_recovered_by_followup():
    client = FakeClient([
        json.dumps(["volcano Iceland eruption", "Iran executed men"]),
        json.dumps(["Giza trains"]),
        "Trains collided [1]. Iran executed men [2].",
    ])
    result = run_research("big news", client, make_docs(), semantic=False)
    assert client.calls == 3
    first = result["coverage"][0]
    assert first["hits"] >= 1 and first["followup"] == "Giza trains"
    assert "followup" not in result["coverage"][1]


def test_still_missing_stays_missing_and_report_still_written():
    client = FakeClient([
        json.dumps(["volcano Iceland eruption", "Iran executed men"]),
        json.dumps(["lava ash Reykjavik"]),
        "Iran executed men [1].",
    ])
    result = run_research("news", client, make_docs(), semantic=False)
    assert client.calls == 3
    assert result["coverage"][0]["hits"] == 0
    assert result["report"] == "Iran executed men [1]."


def test_all_missing_but_followup_finds_news():
    client = FakeClient([
        json.dumps(["volcano Iceland eruption"]),
        json.dumps(["Egypt trains Giza"]),
        "Trains collided [1].",
    ])
    result = run_research("volcano", client, make_docs(), semantic=False)
    assert client.calls == 3
    assert result["report"] == "Trains collided [1]."
    assert len(result["sources"]) == 1


def test_followup_failure_does_not_break_research():
    client = FakeClient([
        json.dumps(["volcano Iceland eruption", "Iran executed men"]),
        RuntimeError("quota"),
        "Iran executed men [1].",
    ])
    result = run_research("news", client, make_docs(), semantic=False)
    assert client.calls == 3
    assert result["coverage"][0]["hits"] == 0
    assert result["report"] == "Iran executed men [1]."


def test_followup_can_be_turned_off():
    client = FakeClient([json.dumps(["volcano Iceland eruption"])])
    result = run_research("volcano", client, make_docs(), semantic=False, followup=False)
    assert client.calls == 1
    assert result["report"] == NO_INFO

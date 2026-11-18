import json

from app.agents.deep_research import MAX_SUBQUESTIONS, parse_plan, run_research
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
        Doc("Cricket final",
            "Cricket final. Pakistan won the cricket final.",
            [("Dawn", "http://dawn/cricket")], "article"),
    ]


def test_parse_plan_handles_fences_garbage_and_wrong_shape():
    assert parse_plan('```json\n["a b", "c d"]\n```', "t") == ["a b", "c d"]
    assert parse_plan("not json", "topic") == ["topic"]
    assert parse_plan('{"x": 1}', "topic") == ["topic"]
    assert parse_plan("[]", "topic") == ["topic"]


def test_parse_plan_dedupes_and_limits():
    many = json.dumps(["Same", "same"] + [f"q{i}" for i in range(10)])
    plan = parse_plan(many, "t")
    assert len(plan) == MAX_SUBQUESTIONS
    assert plan.count("Same") == 1


def test_full_report_uses_two_calls_and_returns_sources():
    client = FakeClient([
        json.dumps(["Egypt trains collided", "Iran executed men"]),
        "Trains collided [1]. Iran executed men [2].",
    ])
    result = run_research("big news", client, make_docs(), semantic=False)
    assert client.calls == 2
    assert result["sub_questions"] == ["Egypt trains collided", "Iran executed men"]
    assert [c["hits"] for c in result["coverage"]] == [1, 1]
    assert len(result["sources"]) == 2


def test_only_cited_sources_are_returned():
    client = FakeClient([json.dumps(["Egypt trains collided"]), "Trains collided [1]."])
    result = run_research("trains", client, make_docs(), semantic=False)
    assert len(result["sources"]) == 1
    assert result["sources"][0]["n"] == 1
    assert result["sources"][0]["title"] == "Egypt trains collided"


def test_no_matching_news_skips_report_call():
    client = FakeClient([json.dumps(["volcano eruption Iceland"]), json.dumps(["lava ash Reykjavik"])])
    result = run_research("volcano eruption Iceland", client, make_docs(), semantic=False)
    assert result["report"] == NO_INFO
    assert result["sources"] == []
    assert client.calls == 2  # plan + ek follow-up search, report call nahi


def test_plan_failure_falls_back_to_topic():
    client = FakeClient([RuntimeError("down"), "Report [1]."])
    result = run_research("Egypt trains collided", client, make_docs(), semantic=False)
    assert result["sub_questions"] == ["Egypt trains collided"]
    assert result["report"] == "Report [1]."
    assert client.calls == 2


def test_empty_report_twice_gives_no_info():
    client = FakeClient([json.dumps(["Egypt trains collided"]), "", ""])
    result = run_research("trains", client, make_docs(), semantic=False)
    assert result["report"] == NO_INFO
    assert client.calls == 3
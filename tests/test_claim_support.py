from types import SimpleNamespace

from app.agents.claim_support import check_claim_support, claim_status, parse_claims
from app.core.story import Story


class FakeClient:
    def __init__(self, text=None, error=None):
        self.calls = 0
        self.text = text
        self.error = error
        self.models = self

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


def story(*outlets):
    return Story(title="T", summary="S", evidence=[(o, f"text from {o}") for o in outlets])


def test_status_rules():
    assert claim_status(["A"], ["B"]) == "disputed"
    assert claim_status(["A", "B"], []) == "confirmed"
    assert claim_status(["A"], []) == "single"


def test_parse_drops_unknown_outlets_and_empty_claims():
    text = (
        '[{"id": 1, "claims": ['
        '{"claim": "Death toll is 12", "supported_by": ["BBC", "Invented"], "contradicted_by": ["Dawn"]},'
        '{"claim": "", "supported_by": ["BBC"]},'
        '{"claim": "Nobody says this", "supported_by": ["Invented"]}]}]'
    )
    result = parse_claims(text, {1: {"BBC", "Dawn"}})
    assert result == {
        1: [
            {
                "claim": "Death toll is 12",
                "supported_by": ["BBC"],
                "contradicted_by": ["Dawn"],
                "status": "disputed",
            }
        ]
    }


def test_parse_survives_garbage():
    assert parse_claims("not json", {1: {"A"}}) == {}
    assert parse_claims('{"id": 1}', {1: {"A"}}) == {}
    assert parse_claims('[{"id": "x"}, 5, {"id": 9, "claims": []}]', {1: {"A"}}) == {}


def test_only_multi_outlet_stories_are_checked():
    multi, single = story("BBC", "Dawn"), story("BBC")
    client = FakeClient(
        '[{"id": 1, "claims": [{"claim": "X happened", "supported_by": ["BBC", "Dawn"], "contradicted_by": []}]}]'
    )
    check_claim_support([single, multi], client)
    assert client.calls == 1
    assert single.claims == []
    assert multi.claims[0]["status"] == "confirmed"


def test_failure_leaves_stories_untouched_and_no_candidates_means_no_call():
    s = story("BBC", "Dawn")
    check_claim_support([s], FakeClient(error=RuntimeError("quota")))
    assert s.claims == []
    client = FakeClient("[]")
    check_claim_support([story("BBC")], client)
    assert client.calls == 0
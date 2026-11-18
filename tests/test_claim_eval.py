from evals.run_eval import evaluate_claims, load_dataset

DATA = load_dataset()


def test_claim_cases_are_well_formed():
    ids = [c["id"] for c in DATA["claims"]]
    assert len(ids) == len(set(ids))
    for case in DATA["claims"]:
        assert len(case["evidence"]) >= 2 and isinstance(case["expected_disputed"], bool)


def make_checker(answer):
    def checker(stories):
        for story, case in zip(stories, DATA["claims"]):
            disputed = answer(case)
            story.claims = [
                {
                    "claim": "x",
                    "supported_by": ["A"],
                    "contradicted_by": ["B"] if disputed else [],
                    "status": "disputed" if disputed else "confirmed",
                }
            ]
        return stories

    return checker


def test_perfect_checker_scores_one():
    result = evaluate_claims(DATA, make_checker(lambda c: c["expected_disputed"]))
    assert result["accuracy"] == 1.0 and result["misses"] == []


def test_checker_that_never_disputes_misses_conflicts():
    result = evaluate_claims(DATA, make_checker(lambda c: False))
    disputed_ids = {c["id"] for c in DATA["claims"] if c["expected_disputed"]}
    assert result["accuracy"] == round(1 - len(disputed_ids) / len(DATA["claims"]), 3)
    assert {m["id"] for m in result["misses"]} == disputed_ids
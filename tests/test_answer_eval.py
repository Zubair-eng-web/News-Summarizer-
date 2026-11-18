from types import SimpleNamespace

from app.agents.research import NO_INFO
from evals.run_eval import evaluate_answers, is_refusal, load_dataset

DATA = load_dataset()
BLOCK = DATA["answers"]
CASES = {c["question"]: c for c in BLOCK["cases"]}
LINKS = {d["id"]: d["link"] for d in BLOCK["docs"]}


def sources_for(case):
    return [
        {"n": 1, "title": "t", "score": 1.0, "sources": [{"source": "S", "link": LINKS[i]}]}
        for i in case["expected_doc_ids"]
    ]


def test_dataset_is_well_formed():
    doc_ids = [d["id"] for d in BLOCK["docs"]]
    assert len(doc_ids) == len(set(doc_ids))
    ids = [c["id"] for c in BLOCK["cases"]]
    assert len(ids) == len(set(ids))
    for case in BLOCK["cases"]:
        assert set(case["expected_doc_ids"]) <= set(doc_ids)
        if case["answerable"]:
            assert case["expected_doc_ids"]
        else:
            assert case["kind"] in ("no_match", "near_miss")
    assert any(not c["answerable"] for c in BLOCK["cases"])


def test_is_refusal():
    assert is_refusal(NO_INFO)
    assert is_refusal("")
    assert is_refusal("The context does not contain the chairman's name.")
    assert not is_refusal("The bank raised rates to five percent [1].")


def test_perfect_answerer_scores_one():
    def answerer(question, docs):
        case = CASES[question]
        if case["answerable"]:
            return {"answer": "Here you go [1].", "sources": sources_for(case)}
        return {"answer": NO_INFO, "sources": []}

    result = evaluate_answers(DATA, answerer)
    assert result["answerable_accuracy"] == 1.0
    assert result["retrieval_hit_rate"] == 1.0 and result["refusal_rate"] == 1.0
    assert result["misses"] == []


def test_never_refusing_is_caught():
    def answerer(question, docs):
        case = CASES[question]
        return {"answer": "A confident answer [1].", "sources": sources_for(case)}

    result = evaluate_answers(DATA, answerer)
    assert result["refusal_rate"] == 0.0
    assert result["answerable_accuracy"] == 1.0
    assert {m["id"] for m in result["misses"]} == {c["id"] for c in BLOCK["cases"] if not c["answerable"]}


def test_always_refusing_is_caught():
    result = evaluate_answers(DATA, lambda question, docs: {"answer": NO_INFO, "sources": []})
    assert result["answerable_accuracy"] == 0.0 and result["retrieval_hit_rate"] == 0.0
    assert result["refusal_rate"] == 1.0


def test_wrong_source_is_a_miss():
    wrong = [{"n": 1, "title": "t", "score": 1.0, "sources": [{"source": "S", "link": "https://nope.example"}]}]
    result = evaluate_answers(DATA, lambda q, d: {"answer": "Answer [1].", "sources": wrong})
    assert result["retrieval_hit_rate"] == 0.0


class FakeModels:
    def generate_content(self, **kwargs):
        if "search query" in kwargs["config"].system_instruction:
            return SimpleNamespace(text=kwargs["contents"])
        return SimpleNamespace(text="Answer [1].")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def test_corpus_is_retrievable_and_unrelated_questions_find_nothing():
    """Asli keyword search + nakli model: har answerable sawal par sahi doc top par, no_match par koi hit nahi."""
    result = evaluate_answers(DATA, client=FakeClient())
    missed = {m["id"] for m in result["misses"]}
    answerable = {c["id"] for c in BLOCK["cases"] if c["answerable"]}
    no_match = {c["id"] for c in BLOCK["cases"] if c.get("kind") == "no_match"}
    assert not (missed & answerable)
    assert not (missed & no_match)
    assert result["retrieval_hit_rate"] == 1.0

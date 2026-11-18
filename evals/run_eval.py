"""Quality evaluation: dedup (precision/recall/F1) and priority (accuracy).

Chalane ka tareeqa:
    python -m evals.run_eval              # dedup (offline, free)
    python -m evals.run_eval --priority   # priority (Gemini API call lagti hai)
    python -m evals.run_eval --answers    # research chat ke jawab (Gemini API call lagti hai)
"""
import json
import sys
from itertools import combinations
from pathlib import Path

from app.core.story import PRIORITIES

DATASET = Path(__file__).with_name("dataset.json")


def load_dataset(path: Path = DATASET) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pairs(groups) -> set:
    return {frozenset(pair) for group in groups for pair in combinations(sorted(group), 2)}


def _ratio(num: int, den: int) -> float:
    return num / den if den else 1.0


def evaluate_dedup(dataset: dict, grouper=None) -> dict:
    """Pairwise precision/recall/F1: har do articles ya to ek story ke hain ya nahi."""
    from app.collectors.rss import Article

    if grouper is None:
        from app.core.dedup import group_duplicates as grouper

    predicted_all: set = set()
    expected_all: set = set()
    wrong_cases = []
    for case in dataset["dedup"]:
        articles = [
            Article(
                title=a["title"],
                link=f"{case['id']}/{a['id']}",
                summary=a.get("summary", ""),
                source=a["source"],
            )
            for a in case["articles"]
        ]
        predicted = _pairs([[a.link for a in group] for group in grouper(articles)])
        expected = _pairs([[f"{case['id']}/{i}" for i in g] for g in case["expected_groups"]])
        predicted_all |= predicted
        expected_all |= expected
        if predicted != expected:
            wrong_cases.append(case["id"])

    tp = len(predicted_all & expected_all)
    precision = _ratio(tp, len(predicted_all))
    recall = _ratio(tp, len(expected_all))
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "cases": len(dataset["dedup"]),
        "wrong_cases": wrong_cases,
    }


def evaluate_priority(dataset: dict, analyzer=None) -> dict:
    """analyzer(stories) -> stories (priority set). Default: asli Gemini analyzer."""
    from app.core.story import Story

    cases = dataset["priority"]
    stories = [Story(title=c["title"], summary=c["summary"], sources=[]) for c in cases]
    if analyzer is None:
        from app.agents.analyzer import analyze_stories
        from app.agents.summarizer import get_client

        client = get_client()

        def analyzer(items):
            return analyze_stories(items, client)

    result = analyzer(stories)
    exact = within_one = 0
    critical_expected = critical_predicted = critical_hit = 0
    misses = []
    for case, story in zip(cases, result):
        want = PRIORITIES.index(case["expected"])
        got = PRIORITIES.index(story.priority) if story.priority in PRIORITIES else 2
        exact += want == got
        within_one += abs(want - got) <= 1
        critical_expected += case["expected"] == "Critical"
        critical_predicted += story.priority == "Critical"
        critical_hit += case["expected"] == "Critical" and story.priority == "Critical"
        if want != got:
            misses.append({"title": case["title"], "expected": case["expected"], "got": story.priority})
    total = len(cases)
    return {
        "accuracy": round(_ratio(exact, total), 3),
        "within_one_tier": round(_ratio(within_one, total), 3),
        "critical_precision": round(_ratio(critical_hit, critical_predicted), 3),
        "critical_recall": round(_ratio(critical_hit, critical_expected), 3),
        "cases": total,
        "misses": misses,
    }


def evaluate_claims(dataset: dict, checker=None) -> dict:
    """Story-level: kya contradictory outlets wali stories 'disputed' pakdi gayin?"""
    from app.core.story import Story

    cases = dataset["claims"]
    stories = [
        Story(title=c["title"], summary="", sources=[], evidence=[tuple(e) for e in c["evidence"]])
        for c in cases
    ]
    if checker is None:
        from app.agents.claim_support import check_claim_support
        from app.agents.summarizer import get_client

        client = get_client()

        def checker(items):
            return check_claim_support(items, client, max_stories=len(items))

    result = checker(stories)
    correct = 0
    misses = []
    for case, story in zip(cases, result):
        disputed = any(c.get("status") == "disputed" for c in story.claims)
        if disputed == case["expected_disputed"]:
            correct += 1
        else:
            misses.append({"id": case["id"], "expected_disputed": case["expected_disputed"]})
    return {"accuracy": round(_ratio(correct, len(cases)), 3), "cases": len(cases), "misses": misses}


REFUSAL_HINTS = (
    "nahi mila",
    "does not contain",
    "do not contain",
    "doesn't contain",
    "not mentioned",
    "no information",
    "does not provide",
    "not provide",
    "cannot answer",
    "can't answer",
    "not covered",
    "nahi hai",
)


def is_refusal(answer: str) -> bool:
    """Heuristic: kya jawab 'collected news me nahi hai' wala inkaar hai?"""
    from app.agents.research import NO_INFO

    text = (answer or "").strip().lower()
    if not text or text == NO_INFO.lower():
        return True
    return any(hint in text for hint in REFUSAL_HINTS)


def evaluate_answers(dataset: dict, answerer=None, client=None) -> dict:
    """Research chat ka jawab: sahi source cite hua? aur jis ka jawab news me nahi, us par inkaar?

    answerer(question, docs) -> {"answer", "sources"}. Default: asli answer_question (keyword search,
    Gemini sirf query rewrite aur jawab ke liye).
    """
    from app.agents.research import Doc

    block = dataset["answers"]
    docs = [
        Doc(
            title=d["title"],
            text=f"{d['title']}. {d['text']}",
            sources=[(d["source"], d["link"])],
            kind="article",
        )
        for d in block["docs"]
    ]
    link_to_id = {d["link"]: d["id"] for d in block["docs"]}
    if answerer is None:
        from app.agents.research import answer_question
        from app.agents.summarizer import get_client

        chosen = client or get_client()

        def answerer(question, items):
            return answer_question(question, client=chosen, docs=items, semantic=False)

    cases = block["cases"]
    answerable = [c for c in cases if c["answerable"]]
    unanswerable = [c for c in cases if not c["answerable"]]
    correct = hits = refused_ok = 0
    misses = []
    for case in cases:
        result = answerer(case["question"], docs)
        refused = is_refusal(result.get("answer", ""))
        cited = {
            link_to_id.get(x.get("link"))
            for s in result.get("sources", [])
            for x in s.get("sources", [])
        }
        if case["answerable"]:
            found = bool(cited & set(case["expected_doc_ids"]))
            hits += found
            if found and not refused:
                correct += 1
            else:
                misses.append({"id": case["id"], "problem": "refused" if refused else "wrong source"})
        elif refused:
            refused_ok += 1
        else:
            misses.append({"id": case["id"], "problem": "answered a question the news cannot answer"})
    return {
        "answerable_accuracy": round(_ratio(correct, len(answerable)), 3),
        "retrieval_hit_rate": round(_ratio(hits, len(answerable)), 3),
        "refusal_rate": round(_ratio(refused_ok, len(unanswerable)), 3),
        "cases": len(cases),
        "misses": misses,
    }


def main(argv=None) -> None:
    args = sys.argv[1:] if argv is None else argv
    data = load_dataset()
    report = {"dedup": evaluate_dedup(data)}
    if "--priority" in args:
        report["priority"] = evaluate_priority(data)
    if "--claims" in args:
        report["claims"] = evaluate_claims(data)
    if "--answers" in args:
        report["answers"] = evaluate_answers(data)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
from app.core.story import PRIORITIES
from evals.run_eval import evaluate_dedup, evaluate_priority, load_dataset

DATA = load_dataset()


def perfect_grouper(articles):
    by_case = {}
    for a in articles:
        by_case.setdefault(a.link.split("/")[0], []).append(a)
    case = DATA["dedup"][[c["id"] for c in DATA["dedup"]].index(articles[0].link.split("/")[0])]
    groups = []
    for expected in case["expected_groups"]:
        groups.append([a for a in articles if a.link.split("/")[1] in expected])
    return groups


def test_dataset_is_consistent():
    ids = [c["id"] for c in DATA["dedup"]]
    assert len(ids) == len(set(ids))
    for case in DATA["dedup"]:
        article_ids = sorted(a["id"] for a in case["articles"])
        grouped = sorted(i for g in case["expected_groups"] for i in g)
        assert article_ids == grouped
    assert all(c["expected"] in PRIORITIES for c in DATA["priority"])


def test_dedup_perfect_grouper_scores_one():
    result = evaluate_dedup(DATA, perfect_grouper)
    assert (result["precision"], result["recall"], result["f1"]) == (1.0, 1.0, 1.0)
    assert result["wrong_cases"] == []


def test_dedup_merge_everything_hurts_precision():
    result = evaluate_dedup(DATA, lambda articles: [list(articles)])
    assert result["recall"] == 1.0
    assert result["precision"] < 1.0
    assert result["wrong_cases"]


def test_dedup_split_everything_hurts_recall():
    result = evaluate_dedup(DATA, lambda articles: [[a] for a in articles])
    assert result["recall"] == 0.0
    assert result["f1"] == 0.0


def test_priority_perfect_analyzer():
    expected = [c["expected"] for c in DATA["priority"]]

    def analyzer(stories):
        for story, priority in zip(stories, expected):
            story.priority = priority
        return stories

    result = evaluate_priority(DATA, analyzer)
    assert result["accuracy"] == 1.0 and result["misses"] == []
    assert result["critical_precision"] == 1.0 and result["critical_recall"] == 1.0


def test_priority_off_by_one_is_counted():
    def analyzer(stories):
        for story in stories:
            story.priority = "Medium"
        return stories

    result = evaluate_priority(DATA, analyzer)
    assert 0 < result["accuracy"] < 1
    assert result["within_one_tier"] > result["accuracy"]
    assert result["critical_recall"] == 0.0
    assert result["misses"]
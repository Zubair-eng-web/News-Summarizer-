from app.agents.research_web import add_web_sources

BASE = {"topic": "t", "report": "r", "sources": []}
GOOD = {"answer": "ok", "grounded": True, "sources": [{"title": "T", "link": "http://a"}]}


def _boom(topic):
    raise AssertionError("checker nahi chalna chahiye")


def test_disabled_leaves_result_untouched():
    assert add_web_sources(BASE, "t", checker=_boom, enabled=False) == BASE


def test_enabled_adds_web_sources():
    result = add_web_sources(BASE, "t", checker=lambda t: GOOD, enabled=True)
    assert result["web"]["sources"][0]["link"] == "http://a"
    assert result["report"] == "r"


def test_ungrounded_answer_is_not_added():
    bad = {"answer": "x", "grounded": False, "sources": []}
    assert add_web_sources(BASE, "t", checker=lambda t: bad, enabled=True) == BASE


def test_checker_failure_never_breaks_research():
    def fail(topic):
        raise RuntimeError("429 quota")

    assert add_web_sources(BASE, "t", checker=fail, enabled=True) == BASE
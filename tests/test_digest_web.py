from app.agents.digest_web import collect_web_checks, pick_for_web_check
from app.agents.email_agent import build_html, build_text
from app.core.story import Story


def _story(title, priority):
    return Story(
        title=title,
        summary="s",
        sources=[("BBC", "https://www.bbc.com")],
        priority=priority,
        sentiment="neutral",
    )


def test_pick_only_critical_and_high_with_limit():
    stories = [_story("a", "Low"), _story("b", "High"), _story("c", "Critical"), _story("d", "High")]
    picked = pick_for_web_check(stories, limit=2)
    assert len(picked) == 2
    assert all(s.priority in ("Critical", "High") for s in picked)


def test_collect_keeps_only_grounded_results():
    stories = [_story("b", "High"), _story("c", "Critical")]

    def checker(text):
        if text == "b":
            return {"grounded": False, "answer": "x", "sources": []}
        return {"grounded": True, "answer": "ok", "sources": [{"title": "T", "link": "https://x.com"}]}

    out = collect_web_checks(stories, checker)
    assert [o["title"] for o in out] == ["c"]


def test_collect_stops_on_first_error():
    calls = []

    def boom(text):
        calls.append(text)
        raise RuntimeError("quota")

    out = collect_web_checks([_story("b", "High"), _story("c", "Critical")], boom)
    assert out == []
    assert len(calls) == 1


def test_email_renders_web_section_and_escapes():
    web = [
        {
            "title": "Quake <b>",
            "answer": "Supported <script>",
            "sources": [{"title": "Src", "link": "https://x.com"}, {"title": "Bad", "link": "javascript:1"}],
        }
    ]
    stories = [_story("Quake", "Critical")]
    html = build_html(stories, "01 Jan 2026", None, web)
    assert "Web check" in html
    assert "<script>" not in html
    assert 'href="javascript:1"' not in html
    assert "https://x.com" in build_text(stories, "01 Jan 2026", None, web)


def test_email_without_web_has_no_web_section():
    stories = [_story("Quake", "Critical")]
    assert "Web check" not in build_html(stories, "01 Jan 2026")
    assert "Web check" not in build_text(stories, "01 Jan 2026")

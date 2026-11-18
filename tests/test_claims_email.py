from app.agents.email_agent import build_html, build_text
from app.core.story import Story


def make(claims):
    story = Story(title="Quake", summary="Summary", sources=[("BBC", "https://b.test")])
    story.claims = claims
    return story


CLAIM = {
    "claim": "Death <b>toll</b> is 12",
    "supported_by": ["BBC"],
    "contradicted_by": ["Dawn"],
    "status": "disputed",
}


def test_claims_appear_escaped_in_html_and_in_text():
    html = build_html([make([CLAIM])], "17 Nov 2026")
    assert "&lt;b&gt;toll&lt;/b&gt;" in html and "<b>toll</b>" not in html
    assert "disputed" in html and "against: Dawn" in html
    text = build_text([make([CLAIM])], "17 Nov 2026")
    assert "[disputed: BBC; against: Dawn]" in text


def test_no_claims_adds_nothing():
    assert "<ul" not in build_html([make([])], "17 Nov 2026")
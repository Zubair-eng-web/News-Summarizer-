from dashboard.oracle import components as ui

STORY = {
    "title": "Big quake",
    "summary": "Strong quake hit the coast. " * 20,
    "sources": [
        {"source": "Bad", "link": "javascript:x"},
        {"source": "BBC", "link": "https://bbc.com/a"},
    ],
}


def test_share_text_has_title_and_first_safe_link():
    text = ui.share_text(STORY)
    assert text.startswith("Big quake")
    assert "https://bbc.com/a" in text
    assert "javascript:" not in text


def test_share_text_summary_is_trimmed():
    assert len(ui.share_text(STORY)) < 450


def test_mailto_is_encoded():
    link = ui.share_mailto({"title": "A & B", "summary": "x", "sources": []})
    assert link.startswith("mailto:?subject=")
    assert "A%20%26%20B" in link
    assert " " not in link
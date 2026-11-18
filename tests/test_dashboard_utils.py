from dashboard import utils


def test_priority_color():
    assert utils.priority_color("Critical") == "#c53030"
    assert utils.priority_color("???") == utils.priority_color("Medium")


def test_format_time():
    assert utils.format_time("2026-11-05T14:30:00") == "05 Nov 2026, 14:30 UTC"
    assert utils.format_time(None) == "-"
    assert utils.format_time("garbage") == "garbage"


def test_sources_markdown():
    md = utils.sources_markdown(
        [
            {"source": "BBC", "link": "http://x.com/a(1)"},
            {"source": "Dawn", "link": ""},
        ]
    )
    assert md == "[BBC](http://x.com/a%281%29) | Dawn"


def test_badge_html_escapes():
    html = utils.badge_html("<b>x</b>", "#000")
    assert "<b>" not in html
    assert "&lt;b&gt;" in html


def test_text_safety_helpers():
    assert utils.md_safe("Cost $1M") == "Cost \\$1M"
    assert utils.html_safe("a<b>$") == "a&lt;b&gt;&#36;"

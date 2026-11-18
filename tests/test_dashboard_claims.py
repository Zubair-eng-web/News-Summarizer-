from dashboard import utils


def test_claims_markdown_formats_and_escapes():
    out = utils.claims_markdown(
        [{"claim": "Toll is $5 [x]", "supported_by": ["BBC"], "contradicted_by": ["Dawn"], "status": "disputed"}]
    )
    assert "\\$5" in out and "(x)" in out
    assert "disputed: BBC; against: Dawn" in out


def test_no_claims_gives_empty_string():
    assert utils.claims_markdown([]) == "" and utils.claims_markdown(None) == ""
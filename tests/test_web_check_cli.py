from app.agents import web_check as wc
from app.agents.research import ResearchError


def test_cli_prints_answer_and_sources(monkeypatch, capsys):
    monkeypatch.setattr(
        wc,
        "web_check",
        lambda text: {"answer": "Supported.", "sources": [{"title": "BBC", "link": "http://b"}]},
    )
    assert wc.main(["some", "claim"]) == 0
    out = capsys.readouterr().out
    assert "Supported." in out and "http://b" in out


def test_cli_quota_error_is_one_clean_message(monkeypatch, capsys):
    def boom(text):
        raise ResearchError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(wc, "web_check", boom)
    assert wc.main(["claim"]) == 1
    out = capsys.readouterr().out
    assert "[ERROR]" in out and "Traceback" not in out


def test_cli_missing_key_message(monkeypatch, capsys):
    def no_key(text):
        raise ValueError("GEMINI_API_KEY set nahi")

    monkeypatch.setattr(wc, "web_check", no_key)
    assert wc.main(["claim"]) == 1
    assert "GEMINI_API_KEY" in capsys.readouterr().out
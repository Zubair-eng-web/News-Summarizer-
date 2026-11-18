from types import SimpleNamespace

import pytest
from google.genai import errors

from app.agents import summarizer
from app.collectors.rss import Article
from app.core.config import settings


class RecordingModels:
    def __init__(self, text="  A summary.  "):
        self.text = text
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(text=self.text)


class FakeClient:
    def __init__(self, text="  A summary.  "):
        self.models = RecordingModels(text)


class Boom(errors.APIError):
    def __init__(self):
        Exception.__init__(self, "quota")

    def __str__(self):
        return "quota"


class BoomModels:
    def generate_content(self, **kwargs):
        raise Boom()


def article(summary="Some text"):
    return Article(title="T", link="http://x.test/1", summary=summary, source="BBC")


def test_get_client_requires_a_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(ValueError):
        summarizer.get_client()


def test_get_client_builds_with_the_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "k-123")
    monkeypatch.setattr(summarizer.genai, "Client", lambda api_key: SimpleNamespace(api_key=api_key))
    assert summarizer.get_client().api_key == "k-123"


def test_empty_reply_falls_back_to_article_text():
    assert summarizer.summarize_article(article("A" * 300), FakeClient("")) == "A" * 200


def test_none_reply_falls_back_to_article_text():
    client = FakeClient()
    client.models.text = None
    assert summarizer.summarize_article(article("short text"), client) == "short text"


def test_api_error_falls_back_to_article_text():
    client = SimpleNamespace(models=BoomModels())
    assert summarizer.summarize_article(article("fallback text"), client) == "fallback text"


def test_prompt_has_source_title_and_truncated_text():
    client = FakeClient()
    summarizer.summarize_article(article("z" * 3000), client)
    contents = client.models.kwargs["contents"]
    assert "Source: BBC" in contents and "Title: T" in contents
    assert contents.count("z") == 1500


def test_summarize_article_builds_client_when_missing(monkeypatch):
    monkeypatch.setattr(summarizer, "get_client", lambda: FakeClient())
    assert summarizer.summarize_article(article()) == "A summary."


def test_summarize_articles_returns_pairs():
    items = [article("one"), article("two")]
    pairs = summarizer.summarize_articles(items, FakeClient())
    assert [a for a, _ in pairs] == items
    assert all(s == "A summary." for _, s in pairs)

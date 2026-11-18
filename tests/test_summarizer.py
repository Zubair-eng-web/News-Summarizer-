from types import SimpleNamespace

from app.agents.summarizer import summarize_article
from app.collectors.rss import Article


class FakeModels:
    def generate_content(self, **kwargs):
        return SimpleNamespace(text="  Fake summary.  ")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def test_summarize_article_returns_clean_text():
    article = Article(title="T", link="http://x.com", summary="Some text", source="BBC")
    result = summarize_article(article, client=FakeClient())
    assert result == "Fake summary."

from types import SimpleNamespace

from app.collectors.rss import Article
from app.pipeline import build_stories


class FakeModels:
    def generate_content(self, **kwargs):
        return SimpleNamespace(text="Fake summary.")


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def make(title, source):
    return Article(title=title, link=f"http://x.com/{source}/{title}", summary="", source=source)


ARTICLES = [
    make("Ronaldo retires from Portugal national team", "BBC"),
    make("Bank of England raises interest rate to fight inflation", "BBC"),
    make("Bank of England lifts interest rate to fight inflation", "Dawn"),
]


def test_duplicates_merge_into_one_story():
    stories = build_stories(ARTICLES, client=FakeClient())
    assert len(stories) == 2
    # Zyada sources wali story sab se upar
    assert len(stories[0].sources) == 2
    assert stories[0].summary == "Fake summary."


def test_max_stories_limit():
    stories = build_stories(ARTICLES, client=FakeClient(), max_stories=1)
    assert len(stories) == 1


def test_empty_articles():
    assert build_stories([]) == []

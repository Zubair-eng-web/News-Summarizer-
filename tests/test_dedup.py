from app.collectors.rss import Article
from app.core.dedup import group_duplicates


def make(title, source="X"):
    return Article(title=title, link=f"http://x.com/{title}", summary="", source=source)


def test_similar_titles_are_grouped():
    articles = [
        make("Bank of England raises interest rate to fight inflation", "BBC"),
        make("Bank of England lifts interest rate to fight inflation", "Dawn"),
        make("Ronaldo retires from Portugal national team", "BBC"),
    ]
    groups = group_duplicates(articles)
    assert len(groups) == 2
    assert len(groups[0]) == 2


def test_different_titles_stay_separate():
    articles = [
        make("Polio case reported in Khyber"),
        make("New solar powered devices announced"),
    ]
    assert len(group_duplicates(articles)) == 2


def test_empty_list():
    assert group_duplicates([]) == []
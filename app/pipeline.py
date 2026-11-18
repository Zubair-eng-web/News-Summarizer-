import time

from app.agents.analyzer import analyze_stories
from app.agents.claim_checker import check_claims
from app.agents.factchecker import check_credibility
from app.agents.ranker import rank_stories
from app.agents.summarizer import get_client, summarize_article
from app.collectors.rss import Article, collect_all
from app.core.dedup import group_duplicates
from app.core.storage import save_new_articles
from app.core.story import Story  # noqa: F401  (doosri files yahin se import karti hain)


def pick_image(group) -> str:
    """First story image found among the grouped articles (from RSS media tags)."""
    for a in group:
        url = (getattr(a, "extra", None) or {}).get("image", "")
        if url:
            return url
    return ""


def build_stories(
    articles: list[Article],
    client=None,
    max_stories: int = 10,
    delay: float = 0.0,
) -> list[Story]:
    """Articles ko merge karke har story ki summary banata hai."""
    if not articles:
        return []

    client = client or get_client()
    groups = group_duplicates(articles)
    groups.sort(key=len, reverse=True)

    stories: list[Story] = []
    for group in groups[:max_stories]:
        main = group[0]
        summary = summarize_article(main, client)
        stories.append(
            Story(
                title=main.title,
                summary=summary,
                sources=[(a.source, a.link) for a in group],
                evidence=[(a.source, f"{a.title}. {a.summary[:400]}") for a in group],
                image_url=pick_image(group),
            )
        )
        if delay:
            time.sleep(delay)  # free tier ki rate limit se bachne ke liye
    return stories


def run_pipeline(
    limit_per_feed: int = 5,
    max_stories: int = 10,
    only_new: bool = True,
    client=None,
    delay: float = 4.0,
    candidate_pool: int = 15,
) -> list[Story]:
    """Collect -> DB save -> dedup -> summarize -> analyze -> rank -> top N."""
    articles = collect_all(limit_per_feed)
    new_articles = save_new_articles(articles)
    print(f"Collected: {len(articles)} | Naye (DB me pehle nahi the): {len(new_articles)}")

    selected = new_articles if only_new else articles
    if not selected:
        return []

    client = client or get_client()
    stories = build_stories(
        selected, client=client, max_stories=max(candidate_pool, max_stories), delay=delay
    )
    analyze_stories(stories, client)
    check_credibility(stories)
    check_claims(stories, client)
    return rank_stories(stories)[:max_stories]


if __name__ == "__main__":
    import sys

    only_new = "--all" not in sys.argv
    stories = run_pipeline(limit_per_feed=5, max_stories=10, only_new=only_new)

    print(f"\nTotal stories: {len(stories)}\n")
    for i, s in enumerate(stories, 1):
        print(f"{i}. [{s.priority} | {s.sentiment} | {s.credibility}] {s.title}")
        print(f"   {s.summary}")
        for src, link in s.sources:
            print(f"   - {src}: {link}")
        print()

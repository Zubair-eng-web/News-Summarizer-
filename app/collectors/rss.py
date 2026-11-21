import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import feedparser
from bs4 import BeautifulSoup

from app.core import source_health
from app.core.safe_fetch import fetch_public
from app.core.user_sources import load_extra_feeds

socket.setdefaulttimeout(10)

# Kuch sites (jaise Al Jazeera) feedparser ke default User-Agent ko block karti hain
feedparser.USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
RETRY_DELAY = 1.5

FEEDS = {
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Dawn": "https://www.dawn.com/feeds/home",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "TechCrunch": "https://techcrunch.com/feed/",
}


@dataclass
class Article:
    title: str
    link: str
    summary: str
    source: str
    published: Optional[datetime] = None
    extra: dict = field(default_factory=dict)


def clean_html(text: str) -> str:
    """HTML tags hata kar plain text return karta hai."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def parse_date(entry) -> Optional[datetime]:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6])
    return None


def _safe_image(url) -> str:
    url = str(url or "").strip()
    return url[:1000] if url.startswith(("http://", "https://")) else ""


def extract_image(entry) -> str:
    """Thumbnail URL from real feed tags only (media, enclosure, link). Empty if none."""
    for key in ("media_thumbnail", "media_content"):
        for item in entry.get(key) or []:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type", ""))
            if item.get("medium") == "video" or kind.startswith("video"):
                continue
            url = _safe_image(item.get("url"))
            if url:
                return url
    for key in ("enclosures", "links"):
        for item in entry.get(key) or []:
            if isinstance(item, dict) and str(item.get("type", "")).startswith("image"):
                url = _safe_image(item.get("href") or item.get("url"))
                if url:
                    return url
    return ""


def image_extra(entry) -> dict:
    url = extract_image(entry)
    return {"image": url} if url else {}


def _parse(url: str, safe: bool, fetcher):
    """safe=True (custom feeds): har redirect hop public check hota hai."""
    if safe:
        return feedparser.parse((fetcher or fetch_public)(url))
    return feedparser.parse(url)


def fetch_feed(
    source: str, url: str, limit: int = 10, safe: bool = False, fetcher=None
) -> list[Article]:
    """Ek feed se articles laata hai. Fail ho to khali list return karta hai."""
    feed = None
    for attempt in range(2):  # ek baar retry: temporary network hiccup se bachne ke liye
        try:
            feed = _parse(url, safe, fetcher)
        except Exception as e:
            print(f"[ERROR] {source}: {e}")
            feed = None
        if feed is not None and feed.entries:
            break
        if attempt == 0:
            time.sleep(RETRY_DELAY)

    if feed is None or not feed.entries:
        print(f"[WARN] {source}: koi article nahi mila")
        return []

    articles = []
    for entry in feed.entries[:limit]:
        articles.append(
            Article(
                title=clean_html(entry.get("title", "")),
                link=entry.get("link", ""),
                summary=clean_html(entry.get("summary", "")),
                source=source,
                published=parse_date(entry),
                extra=image_extra(entry),
            )
        )
    return articles


def collect_all(limit_per_feed: int = 10, extra_feeds: dict | None = None) -> list[Article]:
    """Saari feeds se articles collect karta hai."""
    feeds = dict(FEEDS)
    feeds.update(load_extra_feeds() if extra_feeds is None else extra_feeds)
    all_articles: list[Article] = []
    for source, url in feeds.items():
        if source in FEEDS:
            got = fetch_feed(source, url, limit_per_feed)
        else:
            got = fetch_feed(source, url, limit_per_feed, safe=True)
        if got:
            source_health.record(source, "rss", True, len(got))
        else:
            source_health.record(
                source, "rss", False, 0, "No articles returned (feed unreachable, blocked or empty)"
            )
        all_articles.extend(got)
    return all_articles


if __name__ == "__main__":
    articles = collect_all(limit_per_feed=5)
    print(f"\nTotal articles: {len(articles)}\n")
    for a in articles:
        print(f"[{a.source}] {a.title}")
        print(f"   {a.link}")
        print(f"   {a.published}\n")

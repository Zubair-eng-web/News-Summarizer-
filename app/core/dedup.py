import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.collectors.rss import Article

TITLE_MIN_SHARED = 3      # kam az kam itne common title-lafz
TITLE_MIN_OVERLAP = 0.3   # common / total title-lafz
TEXT_MIN_TITLE_SHARED = 2  # title me kam az kam itne common lafz
TEXT_MIN_SHARED = 4        # title + summary me kam az kam itne common lafz


def title_tokens(title: str) -> set[str]:
    """Title ke important lafz (4+ harf, stop-words ke baghair), pehle 5 harf tak.

    Pehle 5 harf lene se collide/collision, train/trains ek ho jate hain.
    """
    words = re.findall(r"[a-z]{4,}", (title or "").lower())
    return {w[:5] for w in words if w not in ENGLISH_STOP_WORDS}


def same_event_by_title(a: Article, b: Article) -> bool:
    """Do alag outlets ke titles me kaafi common lafz hon to wahi khabar hai."""
    if a.source == b.source:
        return False
    ta, tb = title_tokens(a.title), title_tokens(b.title)
    shared = ta & tb
    union = ta | tb
    if not union or len(shared) < TITLE_MIN_SHARED:
        return False
    return len(shared) / len(union) >= TITLE_MIN_OVERLAP


def text_tokens(a: Article) -> set[str]:
    words = re.findall(r"[a-z]{4,}", f"{a.title} {(a.summary or '')[:300]}".lower())
    return {w[:5] for w in words if w not in ENGLISH_STOP_WORDS}


def same_event_by_text(a: Article, b: Article) -> bool:
    """Title me 2+ aur title+summary me 4+ common lafz (alag outlets) to wahi khabar hai."""
    if a.source == b.source:
        return False
    if len(title_tokens(a.title) & title_tokens(b.title)) < TEXT_MIN_TITLE_SHARED:
        return False
    return len(text_tokens(a) & text_tokens(b)) >= TEXT_MIN_SHARED


def group_duplicates(
    articles: list[Article], threshold: float = 0.5
) -> list[list[Article]]:
    """
    Articles ko groups me baantta hai. Har group ek hi story hai
    jo shayad kai sources ne chhapi ho.
    """
    if not articles:
        return []

    texts = [f"{a.title} {a.summary[:200]}" for a in articles]
    vectors = TfidfVectorizer(stop_words="english").fit_transform(texts)
    sim = cosine_similarity(vectors)

    groups: list[list[Article]] = []
    assigned = set()

    for i in range(len(articles)):
        if i in assigned:
            continue
        group = [articles[i]]
        assigned.add(i)
        for j in range(i + 1, len(articles)):
            if j in assigned:
                continue
            if (
                sim[i][j] >= threshold
                or same_event_by_title(articles[i], articles[j])
                or same_event_by_text(articles[i], articles[j])
            ):
                group.append(articles[j])
                assigned.add(j)
        groups.append(group)

    return groups
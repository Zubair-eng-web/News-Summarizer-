"""Personalization: user keywords used by the ranker.

Priority: keywords saved from the dashboard/API (database) first,
otherwise the INTERESTS value from .env.
"""
import re

from app.core.config import settings

INTERESTS_KEY = "interests"
MAX_INTERESTS = 30
MAX_KEYWORD_LEN = 50


def parse_interests(raw: str) -> list[str]:
    return [k.strip().lower() for k in re.split(r"[,;\n]", raw or "") if k.strip()]


def load_stored_interests() -> str | None:
    """Database me saved value, ya None (kabhi save nahi hui / DB na mile)."""
    try:
        from app.core.storage import get_setting

        return get_setting(INTERESTS_KEY)
    except Exception:
        return None


def get_interests() -> list[str]:
    stored = load_stored_interests()
    return parse_interests(stored if stored is not None else settings.interests)


def save_interests(raw: str) -> list[str]:
    """Keywords clean karke (duplicates hata kar, limit laga kar) save karta hai."""
    from app.core.storage import set_setting

    seen: list[str] = []
    for k in parse_interests(raw):
        k = k[:MAX_KEYWORD_LEN]
        if k not in seen:
            seen.append(k)
    seen = seen[:MAX_INTERESTS]
    set_setting(INTERESTS_KEY, ", ".join(seen))
    return seen


def matches_interests(text: str, interests: list[str]) -> list[str]:
    """Whole-word, case-insensitive match ("ai" matches "AI" but not "said")."""
    low = (text or "").lower()
    return [
        k for k in interests
        if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", low)
    ]
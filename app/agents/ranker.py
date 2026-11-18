from app.core.interests import get_interests, matches_interests
from app.core.story import PRIORITIES, Story


def rank_stories(stories: list[Story], interests: list[str] | None = None) -> list[Story]:
    """Priority first, then interest matches, then number of sources.

    A Medium/Low story matching the user's interests moves up one tier,
    but always ranks after real stories of that tier, and never above High.
    """
    if interests is None:
        interests = get_interests()

    def key(s: Story):
        p = PRIORITIES.index(s.priority) if s.priority in PRIORITIES else 2
        hits = len(matches_interests(f"{s.title} {s.summary}", interests)) if interests else 0
        promoted = 0
        if hits and p > 1:
            p -= 1
            promoted = 1
        return (p, promoted, -hits, -len(s.sources))

    return sorted(stories, key=key)
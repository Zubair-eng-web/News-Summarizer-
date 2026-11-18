from app.core.story import Story


def check_credibility(stories: list[Story]) -> list[Story]:
    """Alag alag outlets ginta hai. Ek hi outlet ke kai articles ek source gine jate hain."""
    for s in stories:
        n = len({src for src, _ in s.sources})
        s.credibility = f"Confirmed by {n} sources" if n >= 2 else "Single source"
    return stories

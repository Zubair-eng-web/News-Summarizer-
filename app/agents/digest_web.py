"""Digest email ke liye web check: top Critical/High stories ko web se verify karta hai."""


def _disputed(story) -> bool:
    if getattr(story, "claim_notes", None):
        return True
    return any(c.get("status") == "disputed" for c in (getattr(story, "claims", None) or []))


def pick_for_web_check(stories, limit: int = 2) -> list:
    chosen = [s for s in stories if s.priority in ("Critical", "High")]
    chosen.sort(key=lambda s: 0 if _disputed(s) else 1)
    return chosen[:limit]


def collect_web_checks(stories, checker, limit: int = 2) -> list[dict]:
    """Har chuni hui story par checker(title) chalata hai. Pehli error par ruk jata hai
    (quota bachane ke liye) aur jo mila wahi wapas deta hai. Kabhi raise nahi karta."""
    results: list[dict] = []
    for story in pick_for_web_check(stories, limit):
        try:
            res = checker(story.title)
        except Exception:
            break
        if res and res.get("grounded"):
            results.append(
                {"title": story.title, "answer": res["answer"], "sources": res["sources"]}
            )
    return results

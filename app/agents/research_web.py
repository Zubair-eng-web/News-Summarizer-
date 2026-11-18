"""Research report me optional web sources (RESEARCH_WEB=true, billed Gemini key chahiye)."""
from app.core.config import settings


def add_web_sources(result: dict, topic: str, checker=None, enabled: bool | None = None) -> dict:
    """Report ke saath web check ke links jodta hai. Koi bhi masla ho to report jaisi hai waisi wapis."""
    if enabled is None:
        enabled = settings.research_web
    if not enabled:
        return result
    try:
        if checker is None:
            from app.agents.web_check import web_check as checker
        web = checker(topic)
    except Exception as e:  # quota/network: report bina web sources ke chalti hai
        print(f"[WARN] Web sources skip: {type(e).__name__}")
        return result
    if not web.get("grounded") or not web.get("sources"):
        return result
    return {**result, "web": {"answer": web.get("answer", ""), "sources": web["sources"]}}
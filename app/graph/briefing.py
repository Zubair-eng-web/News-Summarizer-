import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.alert_agent import send_alert
from app.agents.analyzer import analyze_stories
from app.agents.claim_checker import check_claims
from app.agents.claim_support import check_claim_support
from app.agents.digest_web import collect_web_checks
from app.agents.email_agent import send_email
from app.agents.factchecker import check_credibility
from app.agents.ranker import rank_stories
from app.agents.summarizer import get_client
from app.collectors.rss import collect_all
from app.core.config import settings
from app.core.storage import (
    filter_unalerted,
    get_undigested_articles,
    mark_alerted,
    mark_digested,
    save_new_articles,
)
from app.pipeline import build_stories


class BriefingState(TypedDict, total=False):
    articles: list  # processing ke liye chune gaye articles
    stories: list  # merge + summarize + analyze ke baad stories
    alerts: list  # wo Critical stories jin ka alert abhi jana hai
    sent: bool  # digest email bheji gayi ya nahi
    trace: Annotated[list, operator.add]  # har agent apni line yahan jodta hai


def build_briefing_graph(
    client=None,
    collector=collect_all,
    saver=save_new_articles,
    sender=send_email,
    alert_sender=send_alert,
    alert_filter=filter_unalerted,
    alert_marker=mark_alerted,
    selector=None,
    digest_marker=None,
    story_saver=None,
    video_loader=None,
    web_checker=None,
    limit_per_feed: int = 5,
    max_stories: int = 10,
    candidate_pool: int = 15,
    only_new: bool = True,
    delay: float = 4.0,
):
    """Briefing ka LangGraph banata hai. Saari dependencies inject ho sakti hain (testing ke liye)."""
    holder = {"client": client}
    if web_checker is None and settings.digest_web_check:
        from app.agents.web_check import web_check as web_checker

    def ai():
        # Gemini client tabhi banta hai jab sach me zaroorat ho
        if holder["client"] is None:
            holder["client"] = get_client()
        return holder["client"]

    def collect_node(state: BriefingState):
        everything = collector(limit_per_feed)
        new = saver(everything)
        if not only_new:
            selected = everything
        elif selector is not None:
            selected = selector()  # DB se: wo articles jo abhi tak digest me nahi gaye
        else:
            selected = new
        return {
            "articles": selected,
            "trace": [f"collect: {len(everything)} collected, {len(selected)} to process"],
        }

    def after_collect(state: BriefingState):
        return "summarize" if state.get("articles") else END

    def summarize_node(state: BriefingState):
        stories = build_stories(
            state["articles"],
            client=ai(),
            max_stories=max(candidate_pool, max_stories),
            delay=delay,
        )
        return {"stories": stories, "trace": [f"summarize: {len(stories)} stories"]}

    def analyze_node(state: BriefingState):
        stories = analyze_stories(state["stories"], ai())
        return {"stories": stories, "trace": ["analyze: priority + sentiment done"]}

    def factcheck_node(state: BriefingState):
        stories = check_credibility(state["stories"])
        confirmed = sum(1 for s in stories if s.credibility.startswith("Confirmed"))
        return {"stories": stories, "trace": [f"factcheck: {confirmed} confirmed by 2+ sources"]}

    def claims_node(state: BriefingState):
        try:
            client = ai()
        except Exception as e:
            return {"trace": [f"claims: skipped ({type(e).__name__})"]}
        stories = check_claims(state["stories"], client)
        stories = check_claim_support(stories, client)
        flagged = sum(
            1 for s in stories if s.claim_notes or any(c.get("status") == "disputed" for c in s.claims)
        )
        return {"stories": stories, "trace": [f"claims: {flagged} stories with disputed claims"]}

    def rank_node(state: BriefingState):
        ranked = rank_stories(state["stories"])[:max_stories]
        critical = [s for s in ranked if s.priority == "Critical"]
        alerts = alert_filter(critical) if critical else []
        return {
            "stories": ranked,
            "alerts": alerts,
            "trace": [f"rank: top {len(ranked)} selected, {len(alerts)} new critical"],
        }

    def after_rank(state: BriefingState):
        return "alert" if state.get("alerts") else "email"

    def alert_node(state: BriefingState):
        alert_sender(state["alerts"])
        alert_marker(state["alerts"])  # sirf email jaane ke baad mark hota hai
        return {"trace": [f"alert: breaking alert sent for {len(state['alerts'])} stories"]}

    def email_node(state: BriefingState):
        videos = video_loader() if video_loader is not None else []
        web = collect_web_checks(state["stories"], web_checker) if web_checker else []
        extras = {}
        if videos:
            extras["videos"] = videos
        if web:
            extras["web_checks"] = web
        sender(state["stories"], **extras)
        extra = f" and {len(videos)} videos" if videos else ""
        if story_saver is not None:
            story_saver(state["stories"])
        if digest_marker is not None and only_new:
            digest_marker(state["articles"])  # ab ye dobara digest me nahi aayenge
        return {"sent": True, "trace": [f"email: digest sent with {len(state['stories'])} stories{extra}"]}

    graph = StateGraph(BriefingState)
    graph.add_node("collect", collect_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("factcheck", factcheck_node)
    graph.add_node("claims", claims_node)
    graph.add_node("rank", rank_node)
    graph.add_node("alert", alert_node)
    graph.add_node("email", email_node)

    graph.add_edge(START, "collect")
    graph.add_conditional_edges("collect", after_collect, {"summarize": "summarize", END: END})
    graph.add_edge("summarize", "analyze")
    graph.add_edge("analyze", "factcheck")
    graph.add_edge("factcheck", "claims")
    graph.add_edge("claims", "rank")
    graph.add_conditional_edges("rank", after_rank, {"alert": "alert", "email": "email"})
    graph.add_edge("alert", "email")
    graph.add_edge("email", END)

    return graph.compile()


def run_briefing(**kwargs) -> dict:
    return build_briefing_graph(**kwargs).invoke({"trace": []})


if __name__ == "__main__":
    import sys

    if "--diagram" in sys.argv:
        print(build_briefing_graph(client=object()).get_graph().draw_mermaid())
        raise SystemExit

    options = {"only_new": "--all" not in sys.argv, "selector": get_undigested_articles}
    if "--no-email" in sys.argv:
        options["sender"] = lambda stories, videos=None, web_checks=None: print("(digest email skip ki gayi: --no-email)")
        options["alert_sender"] = lambda stories: print(
            f"(alert skip ki gayi: --no-email, {len(stories)} critical stories)"
        )
        options["alert_marker"] = lambda stories: None  # alert bheji hi nahi, to mark bhi nahi

    if "--no-email" not in sys.argv and "--all" not in sys.argv:
        options["digest_marker"] = mark_digested

    result = run_briefing(**options)

    print("\n--- Agent trace ---")
    for line in result["trace"]:
        print(" ", line)

    stories = result.get("stories", [])
    print(f"\nTotal stories: {len(stories)}\n")
    for i, s in enumerate(stories, 1):
        print(f"{i}. [{s.priority} | {s.sentiment} | {s.credibility}] {s.title}")

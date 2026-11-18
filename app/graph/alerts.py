import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.alert_agent import send_alert, send_telegram_alert
from app.agents.analyzer import analyze_stories
from app.agents.factchecker import check_credibility
from app.agents.summarizer import get_client
from app.collectors.rss import Article, collect_all
from app.core.dedup import group_duplicates
from app.core.storage import filter_unalerted, mark_alerted, save_new_articles
from app.core.story import Story


class AlertState(TypedDict, total=False):
    articles: list
    stories: list
    alerts: list
    trace: Annotated[list, operator.add]


def quick_stories(articles: list[Article]) -> list[Story]:
    """Bina LLM summary ke stories: RSS ki apni description kaafi hoti hai alert ke liye."""
    stories = []
    for group in group_duplicates(articles):
        main = group[0]
        stories.append(
            Story(
                title=main.title,
                summary=main.summary[:300] or main.title,
                sources=[(a.source, a.link) for a in group],
            )
        )
    return stories


def build_alert_graph(
    client=None,
    collector=collect_all,
    saver=save_new_articles,
    alert_sender=send_alert,
    telegram_sender=send_telegram_alert,
    alert_filter=filter_unalerted,
    alert_marker=mark_alerted,
    limit_per_feed: int = 5,
    only_new: bool = True,
):
    """collect -> triage (1 API call) -> alert. Critical na ho to beech me hi ruk jata hai."""
    holder = {"client": client}

    def ai():
        if holder["client"] is None:
            holder["client"] = get_client()
        return holder["client"]

    def collect_node(state: AlertState):
        everything = collector(limit_per_feed)
        new = saver(everything)
        selected = new if only_new else everything
        return {
            "articles": selected,
            "trace": [f"collect: {len(everything)} collected, {len(selected)} to check"],
        }

    def after_collect(state: AlertState):
        return "triage" if state.get("articles") else END

    def triage_node(state: AlertState):
        stories = quick_stories(state["articles"])
        analyze_stories(stories, ai())
        check_credibility(stories)
        critical = [s for s in stories if s.priority == "Critical"]
        alerts = alert_filter(critical) if critical else []
        return {
            "stories": stories,
            "alerts": alerts,
            "trace": [f"triage: {len(stories)} stories checked, {len(alerts)} new critical"],
        }

    def after_triage(state: AlertState):
        return "alert" if state.get("alerts") else END

    def alert_node(state: AlertState):
        alert_sender(state["alerts"])
        telegram_sender(state["alerts"])  # Telegram fail ho to bhi pipeline nahi rukti
        alert_marker(state["alerts"])  # sirf email jaane ke baad mark hota hai
        return {"trace": [f"alert: breaking alert sent for {len(state['alerts'])} stories"]}

    graph = StateGraph(AlertState)
    graph.add_node("collect", collect_node)
    graph.add_node("triage", triage_node)
    graph.add_node("alert", alert_node)

    graph.add_edge(START, "collect")
    graph.add_conditional_edges("collect", after_collect, {"triage": "triage", END: END})
    graph.add_conditional_edges("triage", after_triage, {"alert": "alert", END: END})
    graph.add_edge("alert", END)

    return graph.compile()


def run_alert_check(**kwargs) -> dict:
    return build_alert_graph(**kwargs).invoke({"trace": []})


if __name__ == "__main__":
    import sys

    options = {"only_new": "--all" not in sys.argv}
    if "--no-email" in sys.argv:
        options["alert_sender"] = lambda stories: print(
            f"(alert skip ki gayi: --no-email, {len(stories)} critical stories)"
        )
        options["alert_marker"] = lambda stories: None
        options["telegram_sender"] = lambda stories: None

    result = run_alert_check(**options)

    print("\n--- Alert check trace ---")
    for line in result["trace"]:
        print(" ", line)

    stories = result.get("stories", [])
    if stories:
        print(f"\nChecked stories: {len(stories)}\n")
        for i, s in enumerate(stories, 1):
            print(f"{i}. [{s.priority} | {s.sentiment}] {s.title}")

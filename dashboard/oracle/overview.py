"""Dashboard / Overview page: KPIs, breaking news, source flow, sentiment, system status."""
import streamlit as st

from app.collectors.rss import FEEDS
from dashboard import api_client
from dashboard.oracle import components as ui
from dashboard.oracle import data, logic, theme


def _sources_monitored() -> tuple[int, str]:
    mine = 0
    token = st.session_state.get("token")
    if token:
        try:
            mine = len(api_client.my_sources(token)["sources"])
        except api_client.ApiError:
            mine = 0
    try:
        info = data.oracle_sources()
        rss = sum(1 for r in info["sources"] if r["kind"] == "rss")
        return info["total"], f"{rss} RSS + {info['total'] - rss} YouTube"
    except (api_client.ApiError, KeyError):
        pass
    return len(FEEDS) + mine, f"{len(FEEDS)} built-in RSS + {mine} yours"


def render() -> None:
    ui.page_header("Intelligence Overview", "Live picture of collected news, videos and health.")
    try:
        stats = data.stats()
        stories = data.stories(100)
    except api_client.ApiError as e:
        st.error(str(e))
        return
    try:
        videos = data.videos(50)
    except api_client.ApiError:
        videos = []

    by_pri = stats.get("stories_by_priority", {})
    sources_total, sources_sub = _sources_monitored()
    video_label = "50+" if len(videos) >= 50 else str(len(videos))
    st.markdown(
        ui.kpi_grid(
            [
                ("Total Stories", stats.get("stories", 0), theme.PRIMARY, ""),
                ("Critical News", by_pri.get("Critical", 0), theme.PRIORITY_COLORS["Critical"], ""),
                ("High Priority", by_pri.get("High", 0), theme.PRIORITY_COLORS["High"], ""),
                ("Medium Priority", by_pri.get("Medium", 0), theme.PRIORITY_COLORS["Medium"], ""),
                ("YouTube Videos", video_label, theme.SECONDARY, "summarised videos"),
                ("Sources Monitored", sources_total, theme.PRIMARY, sources_sub),
            ]
        ),
        unsafe_allow_html=True,
    )

    st.markdown("### Breaking News Center")
    try:
        critical = data.stories(5, "Critical")
    except api_client.ApiError:
        critical = []
    if not critical:
        ui.empty_state("No critical stories right now",
                       "Critical stories appear here as soon as the pipeline finds them.")
    for i, story in enumerate(critical, 1):
        ui.story_card(story, i, "crit")

    left, right = st.columns(2)
    with left:
        st.markdown("### Global News Flow")
        rows = logic.source_counts(stories)
        if rows:
            st.altair_chart(ui.bar_chart(rows, "source", "stories", horizontal=True))
        else:
            ui.empty_state("No source data yet", "Run a digest to collect stories.")
        st.caption("World map is not shown: stories carry no location data yet, "
                   "and locations are never guessed.")
    with right:
        st.markdown("### Sentiment Overview")
        if stories:
            st.altair_chart(
                ui.bar_chart(logic.sentiment_counts(stories), "sentiment", "stories",
                             colors=theme.SENTIMENT_COLORS)
            )
        else:
            ui.empty_state("No stories yet")

    st.markdown("### Recently Collected Stories")
    if stories:
        st.markdown("".join(ui.story_row_html(s) for s in stories[:6]), unsafe_allow_html=True)
    else:
        ui.empty_state("Nothing collected yet", "Use Run digest now in the sidebar.")

    st.markdown("### System Status")
    try:
        api_ok = data.health().get("status") == "ok"
    except api_client.ApiError:
        api_ok = False
    latest = stories[0].get("created_at") if stories else None
    st.markdown(ui.status_grid_html(data.system_checks(api_ok, stats, latest)),
                unsafe_allow_html=True)
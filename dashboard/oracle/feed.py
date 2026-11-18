"""News Feed, YouTube Intelligence, Saved Stories and My Personalized Feed pages."""
import streamlit as st

from app.core.category import CATEGORIES
from dashboard import account, api_client, utils
from dashboard.oracle import components as ui
from dashboard.oracle import data, logic

DATE_RANGES = {"All time": 0, "Last 24 hours": 1, "Last 7 days": 7, "Last 30 days": 30}


def _load_bookmarks() -> None:
    """Keep the logged-in user's saved story ids in session state (reloaded per user)."""
    token = st.session_state.get("token")
    if not token:
        return
    user = st.session_state.get("user_email")
    if "bookmark_ids" in st.session_state and st.session_state.get("bookmark_user") == user:
        return
    try:
        st.session_state["bookmark_ids"] = set(api_client.my_bookmarks(token)["story_ids"])
    except api_client.ApiError:
        st.session_state["bookmark_ids"] = set()
    st.session_state["bookmark_user"] = user


def _load_reads() -> None:
    """Keep the logged-in user's read story ids in session state (reloaded per user)."""
    token = st.session_state.get("token")
    if not token:
        return
    user = st.session_state.get("user_email")
    if "read_ids" in st.session_state and st.session_state.get("read_user") == user:
        return
    try:
        st.session_state["read_ids"] = set(api_client.my_reads(token)["story_ids"])
    except api_client.ApiError:
        st.session_state["read_ids"] = set()
    st.session_state["read_user"] = user


def news_feed() -> None:
    ui.page_header("News Feed", "Search, filter, sort and export the collected stories.")
    _load_bookmarks()
    _load_reads()
    limit = st.session_state.get("oracle_limit", 20)
    c1, c2, c3 = st.columns([3, 1.3, 1.3])
    query = c1.text_input("Search", placeholder="Search title or summary", key="nf_q")
    priority = c2.selectbox("Priority", ["All"] + logic.PRIORITIES, key="nf_p")
    sentiment = c3.selectbox("Sentiment", ["All"] + logic.SENTIMENTS, key="nf_s")
    try:
        stories = data.stories(limit, None if priority == "All" else priority)
    except api_client.ApiError as e:
        st.error(str(e))
        return
    c4, c5, c6, c7 = st.columns(4)
    source = c4.selectbox("Source", ["All"] + logic.source_names(stories), key="nf_src")
    category = c5.selectbox("Category", ["All"] + CATEGORIES, key="nf_cat")
    period = c6.selectbox("Date", list(DATE_RANGES), key="nf_date")
    sort = c7.selectbox("Sort by", ["Latest", "Priority"], key="nf_sort")
    shown = logic.filter_stories(
        stories, query, sentiment, source, sort, category, DATE_RANGES[period]
    )
    if st.session_state.get("token") and st.checkbox("Unread only", key="nf_unread"):
        read_ids = st.session_state.get("read_ids", set())
        shown = [s for s in shown if s.get("id") not in read_ids]
    st.caption(f"Showing {len(shown)} of {len(stories)} stories")
    if not shown:
        ui.empty_state("No stories match", "Change the filters or run a digest from the sidebar.")
        return
    st.download_button("Export CSV", logic.stories_csv(shown), file_name="oracle_stories.csv",
                       mime="text/csv", key="nf_csv")
    for i, story in enumerate(shown, 1):
        ui.story_card(story, i, "nf")


def saved() -> None:
    ui.page_header("Saved Stories", "Stories you bookmarked.")
    token = st.session_state.get("token")
    if not token:
        st.info("Login from the sidebar to save and see bookmarked stories.")
        return
    try:
        result = api_client.my_bookmarks(token)
    except api_client.ApiError as e:
        st.error(str(e))
        return
    st.session_state["bookmark_ids"] = set(result["story_ids"])
    st.session_state["bookmark_user"] = st.session_state.get("user_email")
    if not result["stories"]:
        ui.empty_state("Nothing saved yet", "Use the Save button on a story in News Feed.")
        return
    st.caption(f"{result['count']} of {result['limit']} saved")
    for i, story in enumerate(result["stories"], 1):
        ui.story_card(story, i, "saved")


def _video_card(v: dict, n: int) -> None:
    with st.container(key=f"card_yt_{n}"):
        thumb = logic.youtube_thumbnail(v.get("video_id"))
        if thumb:
            st.image(thumb, width=320)
        weak = not v.get("has_transcript")
        label = "Description only (weaker summary)" if weak else "Transcript summary"
        st.caption(f"{v['channel']} | {label} | {utils.format_time(v.get('published'))}")
        st.markdown("**" + utils.link_markdown(v["title"], v["link"]) + "**")
        st.markdown(utils.md_safe(v["summary"]))
        for point in v.get("key_points", []):
            st.markdown("- " + utils.md_safe(point))
        if v.get("takeaway"):
            st.info("Takeaway: " + utils.md_safe(v["takeaway"]))


def youtube() -> None:
    ui.page_header("YouTube Intelligence", "AI summaries, key points and takeaways per video.")
    limit = st.session_state.get("oracle_limit", 20)
    try:
        videos = data.videos(limit)
    except api_client.ApiError as e:
        st.error(str(e))
        return
    c1, c2, c3 = st.columns([3, 1.5, 1.5])
    query = c1.text_input("Search videos", key="yt_q")
    channels = sorted({v.get("channel", "") for v in videos if v.get("channel")})
    channel = c2.selectbox("Channel", ["All"] + channels, key="yt_ch")
    view = c3.selectbox("View", ["Latest", "By channel"], key="yt_view")
    shown = logic.filter_videos(videos, query, channel)
    if not shown:
        ui.empty_state("No video summaries yet", "Use Run videos now in the sidebar.")
        return
    st.caption("Add or remove your own YouTube channels in Sources Management.")
    n = 0
    if view == "By channel":
        for name in sorted({v["channel"] for v in shown}):
            st.markdown("### " + utils.md_safe(name))
            for v in (x for x in shown if x["channel"] == name):
                n += 1
                _video_card(v, n)
    else:
        for v in shown:
            n += 1
            _video_card(v, n)


def my_feed() -> None:
    ui.page_header("My Personalized Feed", "Stories ranked by your own interests.")
    account.render_feed(st.session_state.get("oracle_limit", 20))
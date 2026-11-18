"""Analytics, Alerts, Sources and System Monitoring pages (data from the /oracle/* endpoints)."""
import pandas as pd
import streamlit as st

from dashboard import account, api_client, utils
from dashboard.oracle import components as ui
from dashboard.oracle import data, theme

PERIODS = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
SOURCE_STATUS = {
    "active": "Active",
    "stale": "Stale (no new items for 2+ days)",
    "no_recent": "No new items for 7+ days",
    "no_data": "Nothing collected yet",
}


def _optional(fn, *args):
    try:
        return fn(*args)
    except api_client.ApiError:
        return None


def _chart(title: str, rows: list, category: str, value: str, **kwargs) -> None:
    st.markdown(f"### {title}")
    if rows:
        st.altair_chart(ui.bar_chart(rows, category, value, **kwargs))
    else:
        ui.empty_state("No data in this period")


def analytics() -> None:
    ui.page_header("Analytics Center", "Charts built from the real records in the database.")
    label = st.selectbox("Period", list(PERIODS), index=1, key="an_days")
    try:
        d = data.oracle_analytics(PERIODS[label])
    except api_client.ApiError as e:
        st.error(str(e))
        return
    if not d["total_stories"] and not d["total_videos"]:
        ui.empty_state("No data in this period", "Run a digest or choose a longer period.")
        return
    critical = sum(r["critical"] for r in d["daily"])
    st.markdown(
        ui.kpi_grid([
            ("Stories", d["total_stories"], theme.PRIMARY, label),
            ("Critical", critical, theme.PRIORITY_COLORS["Critical"], label),
            ("Videos summarised", d["total_videos"], theme.SECONDARY, label),
            ("Sources reporting", len(d["sources"]), theme.PRIMARY, ""),
        ]),
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        _chart("News by priority", d["priority"], "priority", "stories",
               colors=theme.PRIORITY_COLORS)
    with right:
        _chart("News by sentiment", d["sentiment"], "sentiment", "stories",
               colors=theme.SENTIMENT_COLORS)
    left, right = st.columns(2)
    with left:
        _chart("News by category", d["categories"], "category", "stories", horizontal=True)
    with right:
        _chart("Frequent terms in titles", d["trending"], "term", "count", horizontal=True)
        st.caption("Simple word counts over story titles (not AI topic modelling).")
    _chart("Daily news collection", d["daily"], "day", "stories")
    _chart("Weekly news trend", d["weekly"], "week", "stories")
    _chart("Critical news history", d["daily"], "day", "critical")
    st.markdown("### Source performance")
    if d["sources"]:
        table = pd.DataFrame(d["sources"]).rename(
            columns={"source": "Source", "stories": "Stories", "critical": "Critical"})
        st.dataframe(table, hide_index=True)
    else:
        ui.empty_state("No data in this period")
    left, right = st.columns(2)
    with left:
        _chart("YouTube video activity", d["video_daily"], "day", "videos")
    with right:
        _chart("Videos by channel", d["video_channels"], "channel", "videos", horizontal=True)


def alerts() -> None:
    ui.page_header("Alerts & Notifications", "Critical stories trigger email and Telegram alerts.")
    try:
        info = data.oracle_alerts()
        critical = data.stories(10, "Critical")
    except api_client.ApiError as e:
        st.error(str(e))
        return
    cfg = info.get("configured", {})
    st.markdown(
        ui.kpi_grid([
            ("Alerts sent (all time)", info["total"], theme.PRIORITY_COLORS["Critical"], ""),
            ("Last 24 hours", info["last_24h"], theme.PRIORITY_COLORS["High"], ""),
            ("Critical stories stored", len(critical), theme.PRIORITY_COLORS["Medium"],
             "latest 10"),
        ]),
        unsafe_allow_html=True,
    )
    checks = [
        {"label": "Email alerts",
         "value": "Configured" if cfg.get("email") else "Not configured",
         "state": "ok" if cfg.get("email") else "warn"},
        {"label": "Telegram alerts",
         "value": "Configured" if cfg.get("telegram") else "Not configured",
         "state": "ok" if cfg.get("telegram") else "neutral"},
    ]
    st.markdown(ui.status_grid_html(checks), unsafe_allow_html=True)
    if st.button("Run alert check now", key="alerts_run"):
        data.run_job("Alert check", api_client.run_alerts)
    st.caption("Each story is alerted only once (the database remembers sent alerts). "
               "Telegram failures never block email. History shows which stories triggered an "
               "alert; per-channel delivery results are not stored.")
    st.markdown("### Alert history")
    rows = info.get("alerts", [])
    if rows:
        st.markdown(
            "".join(
                ui.story_row_html(
                    {"priority": "Critical", "title": a["title"], "created_at": a["sent_at"]}
                )
                for a in rows
            ),
            unsafe_allow_html=True,
        )
    else:
        ui.empty_state("No alerts sent yet", "Alerts appear here after a Critical story is found.")
    st.markdown("### Latest critical stories")
    if critical:
        st.markdown("".join(ui.story_row_html(s) for s in critical), unsafe_allow_html=True)
    else:
        ui.empty_state("No critical stories")
    st.caption("Your own digest and Telegram settings are in Delivery Settings.")


def sources() -> None:
    ui.page_header("Sources Management", "Built-in feeds, channels and your own custom sources.")
    try:
        info = data.oracle_sources()
    except api_client.ApiError as e:
        st.error(str(e))
        info = None
    if info:
        if info["sources"]:
            table = pd.DataFrame([
                {
                    "Source": r["name"],
                    "Type": "RSS" if r["kind"] == "rss" else "YouTube",
                    "Origin": "Built-in" if r["builtin"] else "Custom",
                    "Items stored": r["items"],
                    "Last collected": utils.format_time(r["last_at"]),
                    "Status": SOURCE_STATUS.get(r["status"], r["status"]),
                    "Last checked": utils.format_time(r.get("last_checked")),
                    "Last error": r.get("last_error") or "-",
                }
                for r in info["sources"]
            ])
            st.dataframe(table, hide_index=True)
        else:
            ui.empty_state("No sources configured")
        failing = [r["name"] for r in info["sources"] if r.get("last_error")]
        if failing:
            st.warning("Last collection failed for: " + ", ".join(failing))
        st.caption("Status comes from what was actually stored. Last checked and Last error "
                   "come from the most recent collection run of each RSS feed or YouTube channel.")
    if not st.session_state.get("token"):
        st.info("Login from the sidebar to add your own RSS feeds or YouTube channels.")
        return
    account.render_sources()


def system() -> None:
    ui.page_header("System Monitoring", "Real checks only. Nothing is shown online without proof.")
    try:
        stats = data.stats()
        stories = data.stories(1)
    except api_client.ApiError as e:
        st.error(str(e))
        return
    health = _optional(data.health) or {}
    latest = stories[0].get("created_at") if stories else None
    checks = data.system_checks(health.get("status") == "ok", stats, latest)
    st.markdown(ui.status_grid_html(checks), unsafe_allow_html=True)
    if health.get("debug"):
        st.warning("DEBUG is on. Set DEBUG=false in production.")
    info = _optional(data.oracle_system)
    if info is None:
        st.caption("Job history needs the updated API (/oracle/system).")
    else:
        if info.get("demo_mode"):
            st.info("Demo mode is on: this instance is read-only.")
        st.markdown("### Jobs")
        jobs = [
            {
                "Job": j["job"],
                "Last run": utils.format_time(j["last_run"]),
                "Last result": "OK" if j["last_ok"] else "Failed",
                "Last success": utils.format_time(j["last_success"]),
                "Runs recorded": j["runs"],
            }
            for j in info.get("jobs", [])
        ]
        if jobs:
            st.dataframe(pd.DataFrame(jobs), hide_index=True)
        else:
            ui.empty_state("No job runs recorded yet", "Run a digest or alert check to see history.")
        st.markdown("### Recent errors")
        errors = info.get("recent_errors", [])
        if errors:
            st.dataframe(
                pd.DataFrame([
                    {"Job": e["job"], "When": utils.format_time(e["at"]), "Error": e["error"]}
                    for e in errors
                ]),
                hide_index=True,
            )
        else:
            st.success("No failed runs recorded.")
    runs = _optional(data.oracle_runs, 30)
    if runs and runs.get("runs"):
        st.markdown("### Pipeline run history")
        st.dataframe(
            pd.DataFrame([
                {
                    "Job": r["job"],
                    "Result": "OK" if r["ok"] else "Failed",
                    "Started": utils.format_time(r["started_at"]),
                    "Seconds": round(r["duration_ms"] / 1000, 1),
                    "Note": r["error"] or (r["detail"].splitlines() or [""])[0],
                }
                for r in runs["runs"]
            ]),
            hide_index=True,
        )
    st.caption("Jobs started by the scheduler, the API or the command line are recorded. "
               "History starts from the first run after this update.")
    if st.button("Refresh now", key="system_refresh"):
        data.refresh()
        st.rerun()
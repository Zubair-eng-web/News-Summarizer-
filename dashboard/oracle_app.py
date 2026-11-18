"""ORACLE entry point: streamlit run dashboard/oracle_app.py"""
import hmac
import sys
from pathlib import Path

import streamlit as st

try:
    from dashboard import api_client
except ModuleNotFoundError:  # "streamlit run" me project root path me nahi hota
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dashboard import api_client

from app.core.config import settings
from dashboard.oracle import feed, keys, misc, overview, report, research, sidebar, theme

st.set_page_config(page_title="ORACLE", page_icon="🔮", layout="wide",
                   initial_sidebar_state="expanded")
theme.apply()


def require_password() -> None:
    password = settings.dashboard_password
    if not password or st.session_state.get("authed"):
        return
    holder = st.empty()
    entered = holder.text_input("Password", type="password")
    if entered and hmac.compare_digest(entered.encode(), password.encode()):
        st.session_state.authed = True
        holder.empty()
        return
    if entered:
        st.error("Wrong password")
    st.stop()


require_password()

try:
    api_client.health()
except api_client.ApiError as e:
    st.error(str(e))
    st.stop()

PAGES = [
    ("Overview", "dashboard", "overview", overview.render),
    ("News Feed", "newspaper", "news", feed.news_feed),
    ("YouTube Intelligence", "smart_display", "youtube", feed.youtube),
    ("AI Research", "travel_explore", "research", research.research),
    ("Research Chat", "forum", "chat", research.chat),
    ("My Personalized Feed", "person", "my-feed", feed.my_feed),
    ("Saved Stories", "bookmark", "saved", feed.saved),
    ("Analytics", "bar_chart", "analytics", misc.analytics),
    ("Intelligence Report", "summarize", "report", report.render),
    ("Alerts & Notifications", "notifications_active", "alerts", misc.alerts),
    ("Sources Management", "rss_feed", "sources", misc.sources),
    ("Delivery Settings", "mail", "delivery", misc.delivery),
    ("API Keys", "key", "api-keys", keys.render),
    ("System Monitoring", "monitor_heart", "system", misc.system),
    ("Account & Profile", "account_circle", "account", misc.account_page),
]
nav = st.navigation(
    [
        st.Page(fn, title=title, icon=f":material/{icon}:", url_path=path, default=(path == "overview"))
        for title, icon, path, fn in PAGES
    ]
)
sidebar.render()
nav.run()
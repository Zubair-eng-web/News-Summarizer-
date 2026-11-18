"""Cached API reads for the ORACLE dashboard. Errors (ApiError) are never cached."""
import streamlit as st

from dashboard import api_client
from dashboard.oracle import status


@st.cache_data(ttl=30, show_spinner=False)
def stories(limit: int = 20, priority: str | None = None) -> list[dict]:
    return api_client.get_stories(limit=limit, priority=priority)["stories"]


@st.cache_data(ttl=30, show_spinner=False)
def stats() -> dict:
    return api_client.get_stats()


@st.cache_data(ttl=30, show_spinner=False)
def videos(limit: int = 10) -> list[dict]:
    return api_client.get_videos(limit=limit)["videos"]


@st.cache_data(ttl=10, show_spinner=False)
def health() -> dict:
    return api_client.health()


def refresh() -> None:
    st.cache_data.clear()


def run_job(label: str, fn) -> None:
    try:
        fn()
        st.success(f"{label} started. Press Refresh data in a little while.")
    except api_client.ApiError as e:
        st.warning(str(e))


@st.cache_data(ttl=30, show_spinner=False)
def oracle_analytics(days: int = 30) -> dict:
    return api_client.oracle_analytics(days)


@st.cache_data(ttl=15, show_spinner=False)
def oracle_system() -> dict:
    return api_client.oracle_system()


@st.cache_data(ttl=15, show_spinner=False)
def oracle_alerts() -> dict:
    return api_client.oracle_alerts()


@st.cache_data(ttl=15, show_spinner=False)
def oracle_runs(limit: int = 30) -> dict:
    return api_client.oracle_runs(limit)


@st.cache_data(ttl=30, show_spinner=False)
def oracle_sources() -> dict:
    return api_client.oracle_sources()


def system_checks(api_ok: bool, stats: dict | None, latest_iso: str | None) -> list[dict]:
    """Real checks from /oracle/system; falls back to the basic checks on an older API."""
    try:
        info = oracle_system()
    except api_client.ApiError:
        return status.build_checks(api_ok, stats, latest_iso)
    return status.build_real_checks(api_ok, info)

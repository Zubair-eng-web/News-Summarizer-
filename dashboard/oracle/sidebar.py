"""Shared sidebar controls: data limit, refresh, jobs, global interests, account."""
import streamlit as st

from dashboard import account, api_client
from dashboard.oracle import data


def render() -> None:
    with st.sidebar:
        st.divider()
        st.slider("Stories to load", 5, 50, 20, key="oracle_limit")
        if st.button("Refresh data", key="side_refresh"):
            data.refresh()
            st.rerun()
        with st.expander("Run jobs"):
            if st.button("Run digest now", key="job_digest"):
                data.run_job("Digest", api_client.run_digest)
            if st.button("Run alert check", key="job_alerts"):
                data.run_job("Alert check", api_client.run_alerts)
            if st.button("Run videos now", key="job_videos"):
                data.run_job("Videos", api_client.run_videos)
        with st.expander("Global interests"):
            try:
                current = api_client.get_interests()["interests"]
            except (api_client.ApiError, KeyError):
                current = []
            text = st.text_input(
                "Keywords (comma separated)",
                value=", ".join(current),
                placeholder="cricket, ai, pakistan",
                key="side_interests",
            )
            if st.button("Save interests", key="side_save_interests"):
                try:
                    saved = api_client.save_interests(text)["interests"]
                    st.success("Saved: " + (", ".join(saved) if saved else "none"))
                except api_client.ApiError as e:
                    st.warning(str(e))
        with st.expander("Login / Register"):
            account.render_sidebar()
        if st.button("Clear chat", key="side_clear_chat"):
            st.session_state.messages = []
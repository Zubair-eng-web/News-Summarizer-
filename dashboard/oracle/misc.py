"""Delivery Settings and Account pages. Analytics, Alerts, Sources and System are in ops.py."""
import streamlit as st

from dashboard import account, api_client
from dashboard.oracle import components as ui
from dashboard.oracle.ops import alerts, analytics, sources, system  # noqa: F401


def delivery() -> None:
    ui.page_header("Delivery Settings", "Your daily digest, Telegram chat and digest time.")
    token = st.session_state.get("token")
    if not token:
        st.info("Login from the sidebar to manage delivery settings.")
        return
    account._render_delivery(token)


def account_page() -> None:
    ui.page_header("Account & Profile", "Your login and personal interests.")
    token = st.session_state.get("token")
    if not token:
        st.info("Login or register from the sidebar (Login / Register).")
        return
    st.markdown(f"**Logged in as:** {st.session_state.get('user_email', '')}")
    text = st.text_input("My interests (comma separated)", key="acct_interests")
    if st.button("Save my interests", key="acct_save"):
        try:
            api_client.save_my_interests(token, text)
            st.success("Saved.")
        except api_client.ApiError as e:
            st.warning(str(e))
    if st.button("Logout", key="acct_logout"):
        account._sign_out()
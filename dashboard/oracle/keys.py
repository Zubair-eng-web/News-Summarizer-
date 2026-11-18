"""API Keys page: add or remove extra Gemini keys. The app switches key itself when one runs out."""
import streamlit as st

from dashboard import api_client, utils
from dashboard.oracle import components as ui


def render() -> None:
    ui.page_header("API Keys", "Add extra Gemini keys. When one hits its free quota the next is used.")
    try:
        info = api_client.oracle_keys()
    except api_client.ApiError as e:
        st.error(str(e))
        return
    env = info["env_key"]
    if env["configured"]:
        state = "cooling down (quota)" if env["cooling_down"] else "in use"
        st.markdown(f"**Main key (environment):** `{env['hint']}` - {state}")
    else:
        st.markdown("**Main key (environment):** not set")
    st.markdown(f"### Extra keys ({info['count']} of {info['limit']})")
    if not info["keys"]:
        ui.empty_state("No extra keys yet", "Add one below.")
    for k in info["keys"]:
        c1, c2, c3 = st.columns([2, 3, 1])
        c1.markdown(f"`{k['hint']}`")
        c2.caption(("Cooling down after quota error | " if k["cooling_down"] else "Ready | ")
                   + "added " + utils.format_time(k["created_at"]))
        if info["can_edit"] and c3.button("Remove", key=f"ak_rm_{k['id']}"):
            try:
                api_client.remove_api_key(k["id"])
            except api_client.ApiError as e:
                st.warning(str(e))
            else:
                st.rerun()
    if not info["can_edit"]:
        st.info("Adding or removing keys needs API_KEY to be set and demo mode to be off.")
        return
    n = st.session_state.get("ak_n", 0)
    new_key = st.text_input("New Gemini API key", type="password", key=f"ak_new_{n}")
    if st.button("Add key", key="ak_add") and new_key:
        try:
            api_client.add_api_key(new_key)
        except api_client.ApiError as e:
            st.warning(str(e))
        else:
            st.session_state["ak_n"] = n + 1
            st.rerun()
    st.caption("Keys are stored in the database and shown only as the last 4 characters. "
               "On a free host with SQLite they can be lost on redeploy: use PostgreSQL there.")
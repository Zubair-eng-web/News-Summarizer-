"""Dashboard account UI: login/register in the sidebar and a personalised feed tab."""
import streamlit as st

from dashboard import api_client, utils


def _sign_in(action, email: str, password: str) -> None:
    try:
        result = action(email.strip(), password)
    except api_client.ApiError as e:
        st.warning(str(e))
        return
    st.session_state["token"] = result["access_token"]
    st.session_state["user_email"] = result["user"]["email"]
    st.rerun()


def _sign_out() -> None:
    for key in ("token", "user_email"):
        st.session_state.pop(key, None)
    st.rerun()


def render_sidebar() -> None:
    st.subheader("Account")
    if st.session_state.get("token"):
        st.caption(f"Logged in: {st.session_state.get('user_email', '')}")
        if st.button("Logout"):
            _sign_out()
        return
    email = st.text_input("Email", key="acc_email")
    password = st.text_input("Password (kam az kam 8 harf)", type="password", key="acc_password")
    left, right = st.columns(2)
    if left.button("Login"):
        _sign_in(api_client.login, email, password)
    if right.button("Register"):
        _sign_in(api_client.register, email, password)


HOUR_CHOICES = ["Main digest ke saath"] + [f"{h:02d}:00 UTC" for h in range(24)]


def _render_delivery(token: str) -> None:
    try:
        delivery = api_client.get_delivery(token)
    except api_client.ApiError as e:
        st.warning(str(e))
        return
    hour = delivery.get("digest_hour")
    with st.form("delivery_form"):
        wanted = st.checkbox(
            f"Daily digest meri email par bhejein ({delivery['email']})",
            value=delivery["digest_enabled"],
        )
        chat = st.text_input(
            "Telegram chat id (optional)",
            value=delivery.get("telegram_chat_id", ""),
            placeholder="123456789 ya @channelname",
        )
        choice = st.selectbox(
            "Digest ka waqt (UTC, Pakistan = UTC+5)",
            HOUR_CHOICES,
            index=0 if hour is None else hour + 1,
        )
        saved = st.form_submit_button("Save delivery settings")
    st.caption("Telegram ke liye pehle apne bot ko /start bhejein, phir apni chat id yahan likhein.")
    if saved:
        new_hour = None if choice == HOUR_CHOICES[0] else HOUR_CHOICES.index(choice) - 1
        try:
            api_client.save_delivery(token, wanted, chat.strip(), new_hour)
            st.success("Delivery settings save ho gayi.")
        except api_client.ApiError as e:
            st.warning(str(e))


def render_feed(limit: int) -> None:
    token = st.session_state.get("token")
    if not token:
        st.info("Apni personal feed ke liye sidebar se Login ya Register karein.")
        return

    only_mine = st.checkbox(
        "Dusre users ki custom sources ki stories chhupayein", key="feed_only_mine"
    )
    scope_args = {"scope": "mine"} if only_mine else {}
    try:
        feed = api_client.my_feed(token, limit=limit, **scope_args)
    except api_client.ApiError as e:
        st.warning(f"Feed nahi mili: {e}")
        if st.button("Logout karein", key="feed_logout"):
            _sign_out()
        return

    st.caption("Ye feed sirf aapki interests ke hisab se rank hoti hai.")
    text = st.text_input(
        "Meri interests (comma se alag)",
        value=", ".join(feed["interests"]),
        placeholder="cricket, ai, pakistan",
        key="my_interests",
    )
    if st.button("Save my interests"):
        try:
            api_client.save_my_interests(token, text)
            st.success("Save ho gaya. Feed dobara load hogi.")
            st.rerun()
        except api_client.ApiError as e:
            st.warning(str(e))

    _render_delivery(token)

    if not feed["stories"]:
        st.info("Abhi koi story nahi. Pehle digest chalayein.")
        return
    for i, story in enumerate(feed["stories"], 1):
        with st.container(border=True):
            badges = [
                utils.badge_html(story["priority"], utils.priority_color(story["priority"])),
                utils.badge_html(story["credibility"], utils.NEUTRAL_COLOR),
            ] + [utils.badge_html("match: " + k, "#6b46c1") for k in story["matched_interests"]]
            st.markdown(" &nbsp; ".join(badges), unsafe_allow_html=True)
            st.markdown(
                f'<div style="font-size:18px;font-weight:600;margin:6px 0;">'
                f"{i}. {utils.html_safe(story['title'])}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(utils.md_safe(story["summary"]))
            if story.get("claims"):
                st.markdown(utils.claims_markdown(story["claims"]))
            st.caption("Sources: " + utils.sources_markdown(story.get("sources", [])))


def render_sources() -> None:
    token = st.session_state.get("token")
    if not token:
        return
    st.divider()
    st.subheader("Meri sources")
    try:
        data = api_client.my_sources(token)
    except api_client.ApiError as e:
        st.warning(str(e))
        return
    st.caption(
        f"{len(data['sources'])}/{data['limit']} sources. Ye sources sab ke digest ke liye "
        "collect hoti hain aur '(custom)' label ke saath dikhti hain."
    )
    for src in data["sources"]:
        left, right = st.columns([5, 1])
        left.text(f"{src['name']} [{src['kind']}] {src['url']}")
        if right.button("Delete", key=f"del_src_{src['id']}"):
            try:
                api_client.delete_my_source(token, src["id"])
                st.rerun()
            except api_client.ApiError as e:
                st.warning(str(e))
    kind = st.selectbox("Type", ["rss", "youtube"], key="src_kind")
    name = st.text_input("Naam", key="src_name")
    url = st.text_input("RSS feed URL ya YouTube channel ID (UC...)", key="src_url")
    if st.button("Source add karein"):
        try:
            api_client.add_my_source(token, kind, url, name)
            st.success("Source add ho gayi.")
            st.rerun()
        except api_client.ApiError as e:
            st.warning(str(e))

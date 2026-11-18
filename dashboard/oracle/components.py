"""Reusable ORACLE UI pieces. The *_html helpers are pure so they can be tested offline."""
from html import escape
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st

from dashboard import api_client, utils
from dashboard.oracle import theme


def badge(text, color: str) -> str:
    return f'<span class="badge" style="background:{color}">{escape(str(text))}</span>'


def kpi_html(label, value, accent: str, sub: str = "") -> str:
    sub_html = f'<div class="sub">{escape(str(sub))}</div>' if sub else ""
    return (
        f'<div class="kpi" style="--accent:{accent}">'
        f'<div class="label">{escape(str(label))}</div>'
        f'<div class="value">{escape(str(value))}</div>{sub_html}</div>'
    )


def kpi_grid(items) -> str:
    return '<div class="kpi-grid">' + "".join(kpi_html(*i) for i in items) + "</div>"


def status_html(label: str, value: str, state: str) -> str:
    color = theme.STATE_COLORS.get(state, theme.STATE_COLORS["neutral"])
    return (
        '<div class="status">'
        f'<div class="s-label">{escape(label)}</div>'
        f'<div class="s-value"><span class="dot" style="--c:{color}"></span>{escape(value)}</div>'
        "</div>"
    )


def status_grid_html(checks: list[dict]) -> str:
    cells = "".join(status_html(c["label"], c["value"], c["state"]) for c in checks)
    return f'<div class="status-grid">{cells}</div>'


def empty_html(title: str, hint: str = "") -> str:
    return f'<div class="empty"><b>{escape(title)}</b>{escape(hint)}</div>'


def claim_flag(story: dict) -> bool:
    return any(c.get("status") == "disputed" for c in story.get("claims") or [])


def story_badges_html(story: dict) -> str:
    medium = theme.PRIORITY_COLORS["Medium"]
    parts = [
        badge(story.get("priority", "Medium"),
              theme.PRIORITY_COLORS.get(story.get("priority"), medium)),
        badge(story.get("sentiment", "neutral"),
              theme.SENTIMENT_COLORS.get(story.get("sentiment"), theme.SENTIMENT_COLORS["neutral"])),
        badge(story.get("credibility", "Single source"), "#334155"),
    ]
    if story.get("category"):
        parts.append(badge(story["category"], "#0E7490"))
    if claim_flag(story):
        parts.append(badge("Details differ", theme.PRIORITY_COLORS["High"]))
    for k in story.get("matched_interests") or []:
        parts.append(badge("match: " + k, "#6D28D9"))
    return " ".join(parts)


def story_row_html(story: dict) -> str:
    color = theme.PRIORITY_COLORS.get(story.get("priority"), theme.PRIORITY_COLORS["Medium"])
    return (
        '<div class="row-item">'
        f'{badge(story.get("priority", "Medium"), color)}'
        f'<span class="row-title">{utils.html_safe(story.get("title", ""))}</span>'
        f'<span class="row-time">{escape(utils.format_time(story.get("created_at")))}</span>'
        "</div>"
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="page-title">{escape(title)}</div>'
        f'<div class="page-sub">{escape(subtitle)}</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, hint: str = "") -> None:
    st.markdown(empty_html(title, hint), unsafe_allow_html=True)


def _thumbnail(story: dict) -> None:
    url = str(story.get("image_url") or "")
    if url.startswith(("http://", "https://")):
        st.image(url, width=280)


def _bookmark_button(story: dict, key: str, index: int) -> None:
    token = st.session_state.get("token")
    sid = story.get("id")
    if not token or sid is None:
        return
    saved = sid in st.session_state.get("bookmark_ids", set())
    if st.button("★ Saved" if saved else "☆ Save", key=f"bm_{key}_{index}"):
        try:
            if saved:
                api_client.remove_bookmark(token, sid)
            else:
                api_client.add_bookmark(token, sid)
        except api_client.ApiError as e:
            st.warning(str(e))
            return
        ids = set(st.session_state.get("bookmark_ids", set()))
        ids.symmetric_difference_update({sid})
        st.session_state["bookmark_ids"] = ids
        st.rerun()


def _read_button(story: dict, key: str, index: int) -> None:
    token = st.session_state.get("token")
    sid = story.get("id")
    if not token or sid is None or "read_ids" not in st.session_state:
        return
    is_read = sid in st.session_state["read_ids"]
    if st.button("Mark unread" if is_read else "Mark read", key=f"rd_{key}_{index}"):
        try:
            if is_read:
                api_client.mark_unread(token, sid)
            else:
                api_client.mark_read(token, sid)
        except api_client.ApiError as e:
            st.warning(str(e))
            return
        ids = set(st.session_state["read_ids"])
        ids.symmetric_difference_update({sid})
        st.session_state["read_ids"] = ids
        st.rerun()


def share_text(story: dict) -> str:
    """Plain text to copy: title, short summary and the first safe source link."""
    title = " ".join(str(story.get("title", "")).split())
    summary = " ".join(str(story.get("summary", "")).split())[:300]
    link = next(
        (s["link"] for s in story.get("sources") or []
         if str(s.get("link", "")).startswith(("http://", "https://"))),
        "",
    )
    return "\n".join(part for part in (title, summary, link) if part)


def share_mailto(story: dict) -> str:
    subject = share_text(story).split("\n")[0][:120]
    return "mailto:?subject=" + quote(subject) + "&body=" + quote(share_text(story))


def _share_box(story: dict) -> None:
    if not story.get("title"):
        return
    with st.expander("Share"):
        st.code(share_text(story), language=None)
        st.markdown(f"[Email this story]({share_mailto(story)})")


def story_card(story: dict, index: int, key: str) -> None:
    with st.container(key=f"card_{key}_{index}"):
        _thumbnail(story)
        st.markdown(story_badges_html(story), unsafe_allow_html=True)
        st.markdown(
            f'<div class="story-title">{index}. {utils.html_safe(story.get("title", ""))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(utils.md_safe(story.get("summary", "")))
        if story.get("claims"):
            st.markdown(utils.claims_markdown(story["claims"]))
        sources = story.get("sources") or []
        st.caption(
            f"{utils.format_time(story.get('created_at'))} | Sources: "
            + utils.sources_markdown(sources)
        )
        link = next(
            (s["link"] for s in sources if str(s.get("link", "")).startswith(("http://", "https://"))),
            None,
        )
        if link:
            st.link_button("Read full story", link, key=f"read_{key}_{index}")
        _bookmark_button(story, key, index)
        _read_button(story, key, index)
        _share_box(story)


def render_sources(sources) -> None:
    if not sources:
        return
    with st.expander("Sources"):
        for s in sources:
            links = utils.sources_markdown(s.get("sources", []))
            st.markdown(f"**[{s['n']}]** {utils.md_safe(s['title'])}  \n{links}")


def bar_chart(rows, category: str, value: str, colors: dict | None = None,
              height: int = 260, horizontal: bool = False):
    df = pd.DataFrame(rows)
    if colors:
        color = alt.Color(
            f"{category}:N",
            scale=alt.Scale(domain=list(colors), range=list(colors.values())),
            legend=None,
        )
    else:
        color = alt.value(theme.PRIMARY)
    if horizontal:
        x, y = alt.X(f"{value}:Q", title=None), alt.Y(f"{category}:N", sort="-x", title=None)
    else:
        x, y = alt.X(f"{category}:N", sort=None, title=None), alt.Y(f"{value}:Q", title=None)
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4)
        .encode(x=x, y=y, color=color, tooltip=[category, value])
        .properties(height=height)
        .configure(background="transparent")
        .configure_axis(labelColor=theme.MUTED, titleColor=theme.MUTED,
                        gridColor=theme.BORDER, domainColor=theme.BORDER)
        .configure_view(strokeWidth=0)
    )
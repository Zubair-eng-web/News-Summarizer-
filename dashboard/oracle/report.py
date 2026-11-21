"""Intelligence Report page: daily and weekly report from real stories and videos."""
from collections import Counter
from datetime import datetime, timedelta
from html import escape

import streamlit as st

from dashboard import api_client
from dashboard.oracle import components as ui

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
PERIODS = {"Daily (last 24 hours)": 24, "Weekly (last 7 days)": 24 * 7}


def _link(url) -> str:
    url = str(url or "")
    return url if url.startswith(("http://", "https://")) else ""


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def recent_videos(videos: list[dict], hours: int, now: datetime | None = None) -> list[dict]:
    """Videos published inside the window. Videos with no readable date are kept."""
    now = now or datetime.utcnow()
    cutoff = now - timedelta(hours=hours)
    result = []
    for v in videos:
        try:
            published = datetime.fromisoformat(str(v.get("published")).replace("Z", ""))
            if published.tzinfo:
                published = published.replace(tzinfo=None)
        except ValueError:
            result.append(v)
            continue
        if published >= cutoff:
            result.append(v)
    return result


def summary_counts(stories: list[dict]) -> dict:
    return {
        "total": len(stories),
        "priority": {p: sum(1 for s in stories if s.get("priority") == p) for p in PRIORITY_ORDER},
        "sentiment": dict(Counter(s.get("sentiment", "neutral") for s in stories)),
        "category": dict(Counter(s.get("category") or "Other" for s in stories)),
    }


def _story_sources(story: dict) -> list[tuple[str, str]]:
    out = []
    for s in story.get("sources") or []:
        out.append((_clean(s.get("source")), _link(s.get("link"))))
    return out


def build_markdown(title: str, stories: list[dict], videos: list[dict], generated: str) -> str:
    counts = summary_counts(stories)
    lines = [f"# {title}", "", f"Generated: {generated} (UTC)", ""]
    lines += ["## Summary", "", f"- Stories: {counts['total']}"]
    lines += [f"- {p}: {counts['priority'][p]}" for p in PRIORITY_ORDER]
    if counts["sentiment"]:
        lines.append("- Sentiment: " + ", ".join(f"{k} {v}" for k, v in counts["sentiment"].items()))
    if counts["category"]:
        lines.append("- Categories: " + ", ".join(f"{k} {v}" for k, v in counts["category"].items()))
    lines.append("")
    for p in PRIORITY_ORDER:
        group = [s for s in stories if s.get("priority") == p]
        if not group:
            continue
        lines += [f"## {p} stories ({len(group)})", ""]
        for s in group:
            lines.append(f"- **{_clean(s.get('title'))}** ({s.get('sentiment', 'neutral')}, "
                         f"{_clean(s.get('credibility'))})")
            if s.get("summary"):
                lines.append(f"  {_clean(s['summary'])}")
            srcs = [f"[{n}]({u})" if u else n for n, u in _story_sources(s)]
            if srcs:
                lines.append("  Sources: " + ", ".join(srcs))
        lines.append("")
    if not stories:
        lines += ["No stories in this period.", ""]
    lines += [f"## YouTube highlights ({len(videos)})", ""]
    for v in videos:
        link = _link(v.get("link"))
        name = _clean(v.get("title"))
        lines.append(f"- {'[' + name + '](' + link + ')' if link else name} ({_clean(v.get('channel'))})")
        if v.get("takeaway"):
            lines.append(f"  Takeaway: {_clean(v['takeaway'])}")
    if not videos:
        lines.append("No video summaries in this period.")
    lines.append("")
    return "\n".join(lines)


def build_html(title: str, stories: list[dict], videos: list[dict], generated: str) -> str:
    """Standalone printable page (open it and use Print > Save as PDF)."""
    counts = summary_counts(stories)
    body = [f"<h1>{escape(title)}</h1>", f"<p class='m'>Generated: {escape(generated)} (UTC)</p>"]
    body.append("<p>" + " | ".join(f"{p}: {counts['priority'][p]}" for p in PRIORITY_ORDER)
                + f" | Total: {counts['total']}</p>")
    for p in PRIORITY_ORDER:
        group = [s for s in stories if s.get("priority") == p]
        if not group:
            continue
        body.append(f"<h2>{p} stories ({len(group)})</h2>")
        for s in group:
            srcs = []
            for n, u in _story_sources(s):
                srcs.append(f"<a href='{escape(u)}'>{escape(n)}</a>" if u else escape(n))
            body.append(
                f"<div class='c'><b>{escape(_clean(s.get('title')))}</b>"
                f"<div class='m'>{escape(str(s.get('sentiment', 'neutral')))} | "
                f"{escape(_clean(s.get('credibility')))}</div>"
                f"<div>{escape(_clean(s.get('summary')))}</div>"
                f"<div class='m'>Sources: {', '.join(srcs)}</div></div>"
            )
    body.append(f"<h2>YouTube highlights ({len(videos)})</h2>")
    for v in videos:
        link = _link(v.get("link"))
        name = escape(_clean(v.get("title")))
        head = f"<a href='{escape(link)}'>{name}</a>" if link else name
        body.append(f"<div class='c'><b>{head}</b> <span class='m'>{escape(_clean(v.get('channel')))}</span>"
                    f"<div>{escape(_clean(v.get('takeaway')))}</div></div>")
    css = ("body{font-family:Arial,sans-serif;max-width:820px;margin:24px auto;padding:0 12px;color:#111}"
           ".c{border:1px solid #ddd;border-radius:8px;padding:10px;margin:8px 0}"
           ".m{color:#555;font-size:13px}")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title>"
            f"<style>{css}</style></head><body>{''.join(body)}</body></html>")


def render() -> None:
    ui.page_header("Intelligence Report", "Daily and weekly briefing built from the collected data.")
    period = st.selectbox("Period", list(PERIODS), key="rep_period")
    hours = PERIODS[period]
    try:
        stories = api_client.get_stories(limit=100, hours=hours)["stories"]
        videos = recent_videos(api_client.get_videos(limit=50)["videos"], hours)
    except api_client.ApiError as e:
        st.error(str(e))
        return
    title = "Daily Intelligence Report" if hours == 24 else "Weekly Intelligence Report"
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    counts = summary_counts(stories)
    st.markdown(ui.kpi_grid([
        ("Stories", counts["total"], "#38BDF8"),
        ("Critical", counts["priority"]["Critical"], "#EF4444"),
        ("High", counts["priority"]["High"], "#F97316"),
        ("Videos", len(videos), "#8B5CF6"),
    ]), unsafe_allow_html=True)
    if not stories and not videos:
        ui.empty_state("Nothing in this period", "Run a digest from the sidebar first.")
        return
    markdown = build_markdown(title, stories, videos, generated)
    c1, c2, c3 = st.columns(3)
    stamp = datetime.utcnow().strftime("%Y%m%d")
    c1.download_button("Download Markdown", markdown, file_name=f"oracle_report_{stamp}.md",
                       mime="text/markdown", key="rep_md")
    c2.download_button("Download HTML (print to PDF)", build_html(title, stories, videos, generated),
                       file_name=f"oracle_report_{stamp}.html", mime="text/html", key="rep_html")
    try:
        from dashboard.oracle.pdf_export import build_pdf

        c3.download_button("Download PDF", build_pdf(title, stories, videos, generated),
                           file_name=f"oracle_report_{stamp}.pdf", mime="application/pdf",
                           key="rep_pdf")
    except Exception:
        c3.caption("PDF export needs the fpdf2 package.")
    st.markdown(markdown)
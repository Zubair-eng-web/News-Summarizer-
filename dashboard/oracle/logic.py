"""Pure helpers (no Streamlit): filtering, sorting, counting and exporting stories and videos."""
import csv
import io
import re
from collections import Counter
from datetime import datetime

from dashboard.oracle import status

PRIORITIES = ["Critical", "High", "Medium", "Low"]
SENTIMENTS = ["positive", "negative", "neutral"]
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def source_names(stories: list[dict]) -> list[str]:
    names = {x.get("source") for s in stories for x in s.get("sources") or [] if x.get("source")}
    return sorted(names)


def filter_stories(
    stories: list[dict],
    query: str = "",
    sentiment: str = "All",
    source: str = "All",
    sort: str = "Latest",
    category: str = "All",
    days: int = 0,
    now: datetime | None = None,
) -> list[dict]:
    q = query.strip().lower()
    out = []
    for s in stories:
        if sentiment != "All" and s.get("sentiment") != sentiment:
            continue
        if category != "All" and s.get("category") != category:
            continue
        if source != "All" and source not in {x.get("source") for x in s.get("sources") or []}:
            continue
        if q and q not in f"{s.get('title', '')} {s.get('summary', '')}".lower():
            continue
        if days:
            age = status.age_hours(s.get("created_at"), now)
            if age is None or age > days * 24:
                continue
        out.append(s)
    out.sort(key=lambda s: s.get("created_at") or "", reverse=True)
    if sort == "Priority":
        out.sort(
            key=lambda s: PRIORITIES.index(s["priority"]) if s.get("priority") in PRIORITIES else 9
        )
    return out


def filter_videos(videos: list[dict], query: str = "", channel: str = "All") -> list[dict]:
    q = query.strip().lower()
    out = []
    for v in videos:
        if channel != "All" and v.get("channel") != channel:
            continue
        if q and q not in f"{v.get('title', '')} {v.get('summary', '')}".lower():
            continue
        out.append(v)
    return out


def source_counts(stories: list[dict], top: int = 10) -> list[dict]:
    counts = Counter(x.get("source") for s in stories for x in s.get("sources") or [])
    counts.pop(None, None)
    return [{"source": k, "stories": v} for k, v in counts.most_common(top)]


def sentiment_counts(stories: list[dict]) -> list[dict]:
    counts = Counter(s.get("sentiment") for s in stories)
    return [{"sentiment": k, "stories": counts.get(k, 0)} for k in SENTIMENTS]


def count_by_day(stories: list[dict]) -> list[dict]:
    counts = Counter((s.get("created_at") or "")[:10] for s in stories)
    counts.pop("", None)
    return [{"day": d, "stories": counts[d]} for d in sorted(counts)]


def youtube_thumbnail(video_id) -> str:
    """YouTube's own thumbnail URL for a real 11-character video id, else empty."""
    vid = str(video_id or "")
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if _VIDEO_ID.match(vid) else ""


def _cell(value) -> str:
    text = str(value if value is not None else "")
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text  # spreadsheet formula guard


def stories_csv(stories: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["title", "priority", "sentiment", "category", "credibility",
                     "sources", "created_at", "summary"])
    for s in stories:
        names = "; ".join(x.get("source", "") for x in s.get("sources") or [])
        writer.writerow([_cell(v) for v in (
            s.get("title"), s.get("priority"), s.get("sentiment"), s.get("category"),
            s.get("credibility"), names, s.get("created_at"), s.get("summary"))])
    return buf.getvalue()


_NOT_COVERED = re.compile(r"(?im)^[ \t#*\d.\-]*not covered\b")


def split_report(report: str) -> tuple[str, str]:
    """Split a research report into (main text, 'Not covered' section). Second part may be empty."""
    report = report or ""
    m = _NOT_COVERED.search(report)
    if not m:
        return report.strip(), ""
    return report[: m.start()].rstrip(), report[m.start():].strip()


def research_markdown(result: dict) -> str:
    lines = [f"# Research: {result.get('topic', '')}", "", result.get("report", ""), ""]
    coverage = result.get("coverage") or []
    if coverage:
        lines.append("## Sub-questions")
        for c in coverage:
            line = f"- {c.get('question', '')} ({c.get('hits', 0)} matches)"
            if c.get("followup"):
                line += f" - follow-up search: {c['followup']}"
            lines.append(line)
        lines.append("")
    sources = result.get("sources") or []
    if sources:
        lines.append("## Sources")
        for s in sources:
            links = ", ".join(f"{x.get('source', '')} {x.get('link', '')}".strip()
                              for x in s.get("sources") or [])
            lines.append(f"- [{s.get('n')}] {s.get('title', '')}: {links}")
        lines.append("")
    web = result.get("web")
    if web:
        lines += ["## Web check", web.get("answer", "")]
        for s in web.get("sources") or []:
            lines.append(f"- {s.get('title', '')}: {s.get('link', '')}")
    return "\n".join(lines).strip() + "\n"


def chat_markdown(messages: list[dict]) -> str:
    lines = ["# ORACLE research chat", ""]
    for m in messages:
        who = "You" if m.get("role") == "user" else "ORACLE"
        lines += [f"**{who}:** {m.get('content', '')}", ""]
        for s in m.get("sources") or []:
            links = ", ".join(x.get("link", "") for x in s.get("sources") or [])
            lines.append(f"- [{s.get('n')}] {s.get('title', '')}: {links}")
        if m.get("sources"):
            lines.append("")
    return "\n".join(lines).strip() + "\n"

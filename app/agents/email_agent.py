from collections import Counter
from datetime import datetime
from email.message import EmailMessage
from html import escape

from app.core.config import settings
from app.core.mailer import deliver
from app.core.story import PRIORITIES, Story

PRIORITY_COLORS = {
    "Critical": "#c53030",
    "High": "#dd6b20",
    "Medium": "#2b6cb0",
    "Low": "#718096",
}
SENTIMENT_COLORS = {"positive": "#2f855a", "negative": "#c53030", "neutral": "#718096"}


def count_line(stories: list[Story]) -> str:
    counts = Counter(s.priority for s in stories)
    return " | ".join(f"{p}: {counts[p]}" for p in PRIORITIES if counts[p])


def _safe_link(url: str) -> str:
    url = str(url or "")
    return url if url.startswith(("http://", "https://")) else "#"


def build_videos_html(videos: list[dict] | None) -> str:
    if not videos:
        return ""
    parts = [
        '<h3 style="margin:28px 0 12px 0;border-top:1px solid #e2e8f0;padding-top:16px;">'
        "YouTube Highlights</h3>"
    ]
    for v in videos:
        link = escape(_safe_link(v.get("link")), quote=True)
        points = "".join(f"<li>{escape(str(p))}</li>" for p in v.get("key_points", []))
        points_html = (
            f'<ul style="margin:6px 0 6px 18px;padding:0;color:#333;">{points}</ul>' if points else ""
        )
        note = (
            ""
            if v.get("has_transcript")
            else ' <span style="font-size:12px;color:#b7791f;">(summary sirf description se)</span>'
        )
        takeaway = (
            f'<p style="margin:6px 0 0 0;color:#2c5282;"><b>Takeaway:</b> {escape(v["takeaway"])}</p>'
            if v.get("takeaway")
            else ""
        )
        parts.append(
            '<div style="margin-bottom:20px;">'
            f'<div style="font-size:12px;color:#666;">{escape(str(v.get("channel", "")))}{note}</div>'
            f'<h4 style="margin:2px 0 6px 0;"><a href="{link}" style="color:#1a1a1a;">'
            f'{escape(str(v.get("title", "")))}</a></h4>'
            f'<p style="margin:0 0 6px 0;color:#333;">{escape(str(v.get("summary", "")))}</p>'
            f"{points_html}{takeaway}</div>"
        )
    return "".join(parts)


CLAIM_LABELS = {"confirmed": "confirmed", "disputed": "disputed", "single": "single source"}


def _claim_line(c: dict) -> str:
    label = CLAIM_LABELS.get(c.get("status"), "single source")
    claim = c.get("claim", "")
    who = ", ".join(c.get("supported_by", []))
    against = ", ".join(c.get("contradicted_by", []))
    detail = who + ("; against: " + against if against else "")
    return f"{claim} [{label}: {detail}]"


def claims_text(s) -> list[str]:
    return ["  - " + _claim_line(c) for c in (getattr(s, "claims", None) or [])]


def claims_html(s) -> str:
    claims = getattr(s, "claims", None) or []
    if not claims:
        return ""
    items = "".join("<li>" + escape(_claim_line(c)) + "</li>" for c in claims)
    return '<ul style="margin:0 0 6px 18px;padding:0;font-size:13px;color:#444;">' + items + "</ul>"


def build_web_html(web_checks: list[dict] | None) -> str:
    if not web_checks:
        return ""
    parts = [
        '<h3 style="margin:28px 0 12px 0;border-top:1px solid #e2e8f0;padding-top:16px;">'
        "Web check</h3>"
    ]
    for w in web_checks:
        links = " | ".join(
            f'<a href="{escape(_safe_link(s.get("link")), quote=True)}">'
            f'{escape(str(s.get("title", "")))}</a>'
            for s in w.get("sources", [])
        )
        parts.append(
            '<div style="margin-bottom:18px;">'
            f'<div style="font-weight:bold;">{escape(str(w.get("title", "")))}</div>'
            f'<p style="margin:4px 0;color:#333;">{escape(str(w.get("answer", "")))}</p>'
            f'<p style="margin:0;font-size:13px;color:#666;">Web sources: {links}</p></div>'
        )
    return "".join(parts)


def build_web_text(web_checks: list[dict] | None) -> list[str]:
    if not web_checks:
        return []
    lines = ["Web check", ""]
    for w in web_checks:
        lines.append(str(w.get("title", "")))
        lines.append(str(w.get("answer", "")))
        for s in w.get("sources", []):
            lines.append(f"  {s.get('title', '')}: {s.get('link', '')}")
        lines.append("")
    return lines


def build_html(
    stories: list[Story],
    date_str: str,
    videos: list[dict] | None = None,
    web_checks: list[dict] | None = None,
) -> str:
    if not stories:
        body = "<p>Aaj koi nayi khabar nahi mili.</p>"
    else:
        parts = [
            f'<p style="font-size:13px;color:#555;margin:0 0 18px 0;">{escape(count_line(stories))}</p>'
        ]
        for i, s in enumerate(stories, 1):
            pc = PRIORITY_COLORS.get(s.priority, "#2b6cb0")
            sc = SENTIMENT_COLORS.get(s.sentiment, "#718096")
            links = " | ".join(
                f'<a href="{escape(link, quote=True)}">{escape(src)}</a>'
                for src, link in s.sources
            )
            parts.append(
                '<div style="margin-bottom:22px;">'
                f'<div style="margin-bottom:4px;">'
                f'<span style="background:{pc};color:#fff;font-size:11px;padding:2px 8px;'
                f'border-radius:10px;">{escape(s.priority)}</span> '
                f'<span style="font-size:12px;color:{sc};">{escape(s.sentiment)}</span> '
                f'<span style="font-size:12px;color:#555;">&middot; {escape(s.credibility)}</span></div>'
                f'<h3 style="margin:0 0 6px 0;color:#1a1a1a;">{i}. {escape(s.title)}</h3>'
                f'<p style="margin:0 0 6px 0;color:#333;">{escape(s.summary)}</p>'
                f'{claims_html(s)}'
                f'<p style="margin:0;font-size:13px;color:#666;">Sources: {links}</p>'
                "</div>"
            )
        body = "".join(parts)

    return (
        '<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;">'
        '<h2 style="border-bottom:2px solid #2b6cb0;padding-bottom:8px;">'
        f"Daily Briefing - {escape(date_str)}</h2>"
        f"{body}{build_videos_html(videos)}{build_web_html(web_checks)}"
        '<p style="font-size:12px;color:#999;">Generated by AI Briefing Agent</p>'
        "</div>"
    )


def build_text(
    stories: list[Story],
    date_str: str,
    videos: list[dict] | None = None,
    web_checks: list[dict] | None = None,
) -> str:
    lines = [f"Daily Briefing - {date_str}", ""]
    if stories:
        lines += [count_line(stories), ""]
    for i, s in enumerate(stories, 1):
        lines.append(f"[{s.priority} | {s.sentiment} | {s.credibility}] {i}. {s.title}")
        lines.append(s.summary)
        lines.extend(claims_text(s))
        for src, link in s.sources:
            lines.append(f"   {src}: {link}")
        lines.append("")
    if videos:
        lines += ["YouTube Highlights", ""]
        for v in videos:
            note = "" if v.get("has_transcript") else " (summary sirf description se)"
            lines.append(f"{v.get('title', '')} - {v.get('channel', '')}{note}")
            lines.append(str(v.get("summary", "")))
            for p in v.get("key_points", []):
                lines.append(f"  - {p}")
            if v.get("takeaway"):
                lines.append(f"  Takeaway: {v['takeaway']}")
            lines.append(f"  {v.get('link', '')}")
            lines.append("")
    lines.extend(build_web_text(web_checks))
    return "\n".join(lines)


def build_message(
    stories: list[Story],
    sender: str,
    receiver: str,
    videos: list[dict] | None = None,
    web_checks: list[dict] | None = None,
) -> EmailMessage:
    date_str = datetime.now().strftime("%d %B %Y")
    msg = EmailMessage()
    msg["Subject"] = f"Daily Briefing - {date_str} ({len(stories)} stories)"
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content(build_text(stories, date_str, videos, web_checks))
    msg.add_alternative(build_html(stories, date_str, videos, web_checks), subtype="html")
    return msg


def send_email(
    stories: list[Story],
    smtp_class=None,
    videos: list[dict] | None = None,
    web_checks: list[dict] | None = None,
) -> None:
    deliver(
        lambda sender, receiver: build_message(stories, sender, receiver, videos, web_checks),
        smtp_class=smtp_class,
    )


if __name__ == "__main__":
    import sys
    from pathlib import Path

    from app.agents.factchecker import check_credibility

    sample = [
        Story(
            title="Sample: Major earthquake hits coastal region",
            summary="Ye ek test summary hai. Asli stories pipeline se aayengi.",
            sources=[("BBC", "https://www.bbc.com"), ("Dawn", "https://www.dawn.com")],
            priority="Critical",
            sentiment="negative",
        ),
        Story(
            title="Sample: Bank of England raises rates",
            summary="Ye doosri test summary hai.",
            sources=[("BBC", "https://www.bbc.com")],
            priority="High",
            sentiment="neutral",
        ),
        Story(
            title="Sample: New AI chip announced",
            summary="Ye teesri test summary hai.",
            sources=[("TechCrunch", "https://techcrunch.com")],
            priority="Medium",
            sentiment="positive",
        ),
        Story(
            title="Sample: Football match result",
            summary="Ye chauthi test summary hai.",
            sources=[("Dawn", "https://www.dawn.com")],
            priority="Low",
            sentiment="positive",
        ),
    ]
    sample_videos = [
        {
            "video_id": "sample1",
            "title": "Sample video: Interview on the new budget",
            "link": "https://www.youtube.com",
            "channel": "BBC News",
            "summary": "Ye ek sample video summary hai.",
            "key_points": ["Pehla ahem nukta", "Doosra ahem nukta"],
            "takeaway": "Sab se zaroori baat ek jumle me.",
            "has_transcript": True,
        },
        {
            "video_id": "sample2",
            "title": "Sample video: Short clip without captions",
            "link": "https://www.youtube.com",
            "channel": "Al Jazeera English",
            "summary": "Is video ka transcript nahi mila, is liye summary description se bani.",
            "key_points": [],
            "takeaway": "",
            "has_transcript": False,
        },
    ]
    check_credibility(sample)
    if "--preview" in sys.argv:
        date_str = datetime.now().strftime("%d %B %Y")
        Path("preview.html").write_text(build_html(sample, date_str, sample_videos), encoding="utf-8")
        print("preview.html ban gayi")
    else:
        send_email(sample, videos=sample_videos)
        print(f"Test email bhej di gayi: {settings.email_receiver}")

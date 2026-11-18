from datetime import datetime
from email.message import EmailMessage
from html import escape

from app.agents.email_agent import PRIORITY_COLORS, SENTIMENT_COLORS, _safe_link, build_videos_html
from app.core.mailer import deliver
from app.core.story import PRIORITIES, SENTIMENTS

STATUS_COLORS = {"new": "#2f855a", "rising": "#dd6b20", "falling": "#718096", "steady": "#4a5568"}
NO_PREVIOUS_NOTE = "Pichle hafte ka data nahi hai, muqabla agle hafte se shuru hoga."


def _range_label(report: dict) -> str:
    start = datetime.fromisoformat(report["start"])
    end = datetime.fromisoformat(report["end"])
    return f"{start:%d %b} - {end:%d %b %Y}"


def _delta(current: int, previous: int, has_previous: bool) -> str:
    if not has_previous:
        return ""
    diff = current - previous
    if diff > 0:
        return f"+{diff}"
    return str(diff) if diff < 0 else "0"


def _stats_table(report: dict, key: str, values: list[str], colors: dict) -> str:
    has_prev = report["has_previous"]
    head = '<th align="left" style="padding:4px 8px;"></th><th align="right" style="padding:4px 8px;">This week</th>'
    if has_prev:
        head += (
            '<th align="right" style="padding:4px 8px;">Last week</th>'
            '<th align="right" style="padding:4px 8px;">Change</th>'
        )
    rows = []
    for value in values:
        entry = report[key][value]
        color = colors.get(value, "#4a5568")
        cells = (
            f'<td style="padding:4px 8px;color:{color};font-weight:bold;">{escape(value)}</td>'
            f'<td align="right" style="padding:4px 8px;">{entry["count"]}</td>'
        )
        if has_prev:
            change = _delta(entry["count"], entry["previous"], True)
            cells += (
                f'<td align="right" style="padding:4px 8px;">{entry["previous"]}</td>'
                f'<td align="right" style="padding:4px 8px;">{change}</td>'
            )
        rows.append(f"<tr>{cells}</tr>")
    return (
        '<table style="border-collapse:collapse;font-size:14px;margin-bottom:14px;">'
        f"<tr>{head}</tr>{''.join(rows)}</table>"
    )


def build_weekly_html(report: dict) -> str:
    has_prev = report["has_previous"]
    parts = []

    if report.get("overview"):
        parts.append(
            '<p style="background:#f7fafc;border-left:4px solid #2b6cb0;padding:12px;'
            f'margin:0 0 20px 0;color:#2d3748;">{escape(report["overview"])}</p>'
        )

    if not report["total"]:
        parts.append("<p>Is hafte koi story nahi mili.</p>")
    else:
        line = f'Stories this week: <b>{report["total"]}</b>'
        if has_prev:
            change = _delta(report["total"], report["previous_total"], True)
            line += f' (last week: {report["previous_total"]}, change: {change})'
        parts.append(f'<p style="margin:0 0 10px 0;">{line}</p>')
        if not has_prev:
            parts.append(f'<p style="font-size:12px;color:#888;margin:0 0 12px 0;">{NO_PREVIOUS_NOTE}</p>')

        parts.append('<h3 style="margin:20px 0 8px 0;">By priority</h3>')
        parts.append(_stats_table(report, "priority", PRIORITIES, PRIORITY_COLORS))
        parts.append('<h3 style="margin:20px 0 8px 0;">By sentiment</h3>')
        parts.append(_stats_table(report, "sentiment", SENTIMENTS, SENTIMENT_COLORS))

        parts.append('<h3 style="margin:20px 0 8px 0;">Trending Topics</h3>')
        if report["trending"]:
            items = []
            for t in report["trending"]:
                badge = ""
                extra = f'{t["count"]} stories'
                if has_prev:
                    color = STATUS_COLORS.get(t["status"], "#4a5568")
                    badge = (
                        f'<span style="background:{color};color:#fff;font-size:11px;padding:1px 8px;'
                        f'border-radius:10px;">{escape(t["status"])}</span> '
                    )
                    extra += f' (last week: {t["previous"]})'
                items.append(f'<li style="margin-bottom:6px;">{badge}<b>{escape(t["term"])}</b> - {extra}</li>')
            parts.append('<ul style="margin:0 0 14px 18px;padding:0;">' + "".join(items) + "</ul>")
        else:
            parts.append('<p style="color:#888;">Abhi kaafi data nahi, trends agle hafte dikhenge.</p>')

        parts.append('<h3 style="margin:20px 0 8px 0;">Top Stories of the Week</h3>')
        for i, s in enumerate(report["top_stories"], 1):
            color = PRIORITY_COLORS.get(s.get("priority"), "#2b6cb0")
            links = " | ".join(
                f'<a href="{escape(_safe_link(x.get("link")), quote=True)}">{escape(str(x.get("source", "")))}</a>'
                for x in s.get("sources", [])
            )
            parts.append(
                '<div style="margin-bottom:18px;">'
                f'<span style="background:{color};color:#fff;font-size:11px;padding:2px 8px;'
                f'border-radius:10px;">{escape(str(s.get("priority", "")))}</span> '
                f'<span style="font-size:12px;color:#555;">{escape(str(s.get("credibility", "")))}</span>'
                f'<h4 style="margin:4px 0 6px 0;color:#1a1a1a;">{i}. {escape(s["title"])}</h4>'
                f'<p style="margin:0 0 6px 0;color:#333;">{escape(s.get("summary", ""))}</p>'
                f'<p style="margin:0;font-size:13px;color:#666;">Sources: {links}</p></div>'
            )

    parts.append(build_videos_html(report.get("videos")))

    return (
        '<div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;">'
        '<h2 style="border-bottom:2px solid #2b6cb0;padding-bottom:8px;">'
        f"Weekly Intelligence Report</h2>"
        f'<p style="color:#666;margin:0 0 16px 0;">{escape(_range_label(report))}</p>'
        f'{"".join(parts)}'
        '<p style="font-size:12px;color:#999;">Generated by AI Briefing Agent</p>'
        "</div>"
    )


def build_weekly_text(report: dict) -> str:
    has_prev = report["has_previous"]
    lines = [f"Weekly Intelligence Report - {_range_label(report)}", ""]
    if report.get("overview"):
        lines += [report["overview"], ""]

    if not report["total"]:
        lines.append("Is hafte koi story nahi mili.")
    else:
        total = f"Stories this week: {report['total']}"
        if has_prev:
            total += f" (last week: {report['previous_total']}, {_delta(report['total'], report['previous_total'], True)})"
        lines.append(total)
        if not has_prev:
            lines.append(NO_PREVIOUS_NOTE)
        lines.append("")

        for title, key, values in (("Priority", "priority", PRIORITIES), ("Sentiment", "sentiment", SENTIMENTS)):
            parts = []
            for v in values:
                e = report[key][v]
                text = f"{v} {e['count']}"
                if has_prev:
                    text += f" ({_delta(e['count'], e['previous'], True)})"
                parts.append(text)
            lines.append(f"{title}: " + " | ".join(parts))
        lines.append("")

        lines.append("Trending topics:")
        if report["trending"]:
            for t in report["trending"]:
                extra = f" [{t['status']}, last week: {t['previous']}]" if has_prev else ""
                lines.append(f"  - {t['term']} ({t['count']} stories){extra}")
        else:
            lines.append("  Abhi kaafi data nahi.")
        lines.append("")

        lines.append("Top stories:")
        for i, s in enumerate(report["top_stories"], 1):
            lines.append(f"  {i}. [{s.get('priority')}] {s['title']}")
            lines.append(f"     {s.get('summary', '')}")
            for x in s.get("sources", []):
                lines.append(f"     {x.get('source')}: {x.get('link')}")
        lines.append("")

    if report.get("videos"):
        lines.append("YouTube Highlights:")
        for v in report["videos"]:
            lines.append(f"  - {v.get('title', '')} ({v.get('channel', '')})")
            lines.append(f"    {v.get('summary', '')}")
            lines.append(f"    {v.get('link', '')}")
    return "\n".join(lines)


def build_weekly_message(report: dict, sender: str, receiver: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"Weekly Intelligence Report - {_range_label(report)}"
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content(build_weekly_text(report))
    msg.add_alternative(build_weekly_html(report), subtype="html")
    return msg


def send_weekly_email(report: dict, smtp_class=None) -> None:
    deliver(
        lambda sender, receiver: build_weekly_message(report, sender, receiver),
        smtp_class=smtp_class,
    )

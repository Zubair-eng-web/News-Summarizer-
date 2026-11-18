from datetime import datetime
from html import escape

PRIORITY_COLORS = {
    "Critical": "#c53030",
    "High": "#dd6b20",
    "Medium": "#2b6cb0",
    "Low": "#718096",
}
SENTIMENT_COLORS = {"positive": "#2f855a", "negative": "#c53030", "neutral": "#718096"}
NEUTRAL_COLOR = "#4a5568"


def priority_color(priority: str) -> str:
    return PRIORITY_COLORS.get(priority, PRIORITY_COLORS["Medium"])


def sentiment_color(sentiment: str) -> str:
    return SENTIMENT_COLORS.get(sentiment, SENTIMENT_COLORS["neutral"])


def format_time(iso: str | None) -> str:
    """DB ka waqt UTC me hota hai."""
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M UTC")
    except ValueError:
        return str(iso)


def badge_html(text: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:10px;font-size:12px;">{escape(text)}</span>'
    )


def md_safe(text: str) -> str:
    """Markdown me '$' se math ban jata hai (jaise '$1M'), is liye escape."""
    return text.replace("$", "\\$")


def html_safe(text: str) -> str:
    return escape(text).replace("$", "&#36;")


def sources_markdown(sources: list[dict]) -> str:
    parts = []
    for s in sources:
        name = str(s.get("source", "source")).replace("[", "").replace("]", "")
        link = str(s.get("link", ""))
        if link.startswith(("http://", "https://")):
            link = link.replace("(", "%28").replace(")", "%29")
            parts.append(f"[{name}]({link})")
        else:
            parts.append(name)
    return " | ".join(parts)


CLAIM_LABELS = {"confirmed": "confirmed", "disputed": "disputed", "single": "single source"}


def _plain(text) -> str:
    return md_safe(str(text).replace("[", "(").replace("]", ")"))


def claims_markdown(claims) -> str:
    """Story ke claims ki bullet list (confirmed / disputed / single source)."""
    lines = []
    for c in claims or []:
        label = CLAIM_LABELS.get(c.get("status"), "single source")
        who = ", ".join(c.get("supported_by", []))
        against = ", ".join(c.get("contradicted_by", []))
        detail = who + ("; against: " + against if against else "")
        lines.append(f"- {_plain(c.get('claim', ''))} _[{label}: {_plain(detail)}]_")
    return "\n".join(lines)


def link_markdown(text: str, url: str) -> str:
    """Markdown link. Title ke [ ] badal deta hai taake link na toote."""
    label = md_safe(str(text).replace("[", "(").replace("]", ")"))
    if not str(url).startswith(("http://", "https://")):
        return label
    safe = str(url).replace("(", "%28").replace(")", "%29")
    return f"[{label}]({safe})"

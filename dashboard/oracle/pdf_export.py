"""PDF export for the Intelligence Report (fpdf2, built-in fonts, latin-1 only)."""
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
_REPL = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "...",
}


def _text(value, width: int = 60) -> str:
    s = " ".join(str(value or "").split())
    for a, b in _REPL.items():
        s = s.replace(a, b)
    s = s.encode("latin-1", "replace").decode("latin-1")
    words = []
    for w in s.split(" "):
        while len(w) > width:
            words.append(w[:width])
            w = w[width:]
        words.append(w)
    return " ".join(words)


def build_pdf(title: str, stories: list[dict], videos: list[dict], generated: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()

    def line(value, size=10, style="", h=5):
        text = _text(value)
        if not text:
            return
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")

    line(title, 18, "B", 9)
    line(f"Generated: {generated} (UTC)", 9)
    counts = " | ".join(
        f"{p}: {sum(1 for s in stories if s.get('priority') == p)}" for p in PRIORITY_ORDER
    )
    line(f"{counts} | Total: {len(stories)}", 10, "B")
    pdf.ln(3)
    for p in PRIORITY_ORDER:
        group = [s for s in stories if s.get("priority") == p]
        if not group:
            continue
        line(f"{p} stories ({len(group)})", 13, "B", 7)
        for s in group:
            line(s.get("title"), 10, "B")
            line(f"{s.get('sentiment', 'neutral')} | {s.get('credibility', '')}", 8)
            line(s.get("summary"), 9)
            names = ", ".join(str(x.get("source", "")) for x in s.get("sources") or [])
            line(f"Sources: {names}" if names else "", 8)
            pdf.ln(2)
    if not stories:
        line("No stories in this period.")
    pdf.ln(2)
    line(f"YouTube highlights ({len(videos)})", 13, "B", 7)
    for v in videos:
        line(f"{v.get('title', '')} ({v.get('channel', '')})", 10, "B")
        line(v.get("takeaway"), 9)
        pdf.ln(2)
    if not videos:
        line("No video summaries in this period.")
    return bytes(pdf.output())

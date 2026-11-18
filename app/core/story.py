from dataclasses import dataclass, field

PRIORITIES = ["Critical", "High", "Medium", "Low"]
SENTIMENTS = ["positive", "negative", "neutral"]


@dataclass
class Story:
    title: str
    summary: str
    sources: list[tuple[str, str]] = field(default_factory=list)  # (source, link)
    priority: str = "Medium"
    sentiment: str = "neutral"
    credibility: str = "Single source"
    evidence: list[tuple[str, str]] = field(default_factory=list)  # (source, title + snippet), DB me save nahi hota
    claim_notes: str = ""
    claims: list = field(default_factory=list)
    image_url: str = ""  # [{claim, supported_by, contradicted_by, status}]

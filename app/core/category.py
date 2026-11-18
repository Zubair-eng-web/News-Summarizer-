"""Rule-based story categories. No LLM call and no stored column: computed when read."""
import re

_RULES = {
    "Politics": [
        r"\bgovernment", r"\bminister", r"\bpresident", r"\bparliament", r"\belection",
        r"\bsenate", r"\bcongress", r"\bpolic(?:y|ies)\b", r"\bdiplomat", r"\bsanction",
        r"\btreaty", r"\bimmigration", r"\bimpeach", r"\bvote",
    ],
    "Conflict": [
        r"\bwar\b", r"\bstrike", r"\bmilitary", r"\bmissile", r"\bairstrike", r"\battack",
        r"\bceasefire", r"\btroops", r"\bdrone", r"\bhostage", r"\bbomb", r"\binvasion",
        r"\bconflict",
    ],
    "Business": [
        r"\beconom", r"\binflation", r"\bbank", r"\bstock", r"\bmarket", r"\bloan",
        r"\btrade\b", r"\btariff", r"\bprofit", r"\bshares\b", r"\binterest rate",
        r"\bbudget", r"\bwage", r"\binvest",
    ],
    "Technology": [
        r"\bai\b", r"\bartificial intelligence", r"\bsoftware", r"\btech\b", r"\bchip",
        r"\bnvidia", r"\bopen-source", r"\bcyber", r"\bstartup", r"\brobot", r"\bgpu",
        r"\bsmartphone", r"\bdata cent",
    ],
    "Sports": [
        r"\bcricket", r"\bfootball", r"\bbasketball", r"\bmatch\b", r"\btournament",
        r"\bleague", r"\bolympic", r"\bsquad", r"\bcoach", r"\bchampion",
    ],
    "Health": [
        r"\bhealth", r"\bhospital", r"\bdisease", r"\bvirus", r"\bvaccine", r"\bmedical",
        r"\bcancer", r"\boutbreak", r"\bdoctor", r"\bpatient",
    ],
    "Disaster": [
        r"\bearthquake", r"\bflood", r"\bstorm", r"\bcyclone", r"\bwildfire", r"\bdrought",
        r"\bhurricane", r"\blandslide", r"\btsunami", r"\bdisaster", r"\bheatwave",
        r"\bcollision", r"\bcrash",
    ],
    "Crime": [
        r"\barrest", r"\bpolice", r"\bmurder", r"\bsmuggl", r"\bfraud", r"\btheft",
        r"\bhoax", r"\bkidnap", r"\bterror", r"\bsentenced",
    ],
}
CATEGORIES = list(_RULES) + ["Other"]
_COMPILED = {name: [re.compile(p) for p in pats] for name, pats in _RULES.items()}


def categorize(title: str, summary: str = "") -> str:
    """Title match = 2 points, summary match = 1 point. No match = Other."""
    head, body = (title or "").lower(), (summary or "").lower()
    best, best_score = "Other", 0
    for name, patterns in _COMPILED.items():
        score = sum(2 * bool(p.search(head)) + bool(p.search(body)) for p in patterns)
        if score > best_score:
            best, best_score = name, score
    return best
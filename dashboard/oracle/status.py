"""System status checks built only from real API answers (nothing is faked)."""
from datetime import datetime, timezone


def age_hours(iso: str | None, now: datetime | None = None) -> float | None:
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if t.tzinfo:
        t = t.astimezone(timezone.utc).replace(tzinfo=None)
    now = now or datetime.utcnow()
    return max((now - t).total_seconds() / 3600, 0.0)


def freshness_label(hours: float | None) -> str:
    if hours is None:
        return "No data yet"
    if hours < 1:
        return "Under 1 hour ago"
    if hours < 48:
        return f"{int(hours)} h ago"
    return f"{int(hours // 24)} days ago"


def freshness_state(hours: float | None) -> str:
    if hours is None:
        return "neutral"
    if hours <= 36:
        return "ok"
    return "warn" if hours <= 96 else "bad"


def build_checks(api_ok: bool, stats: dict | None, latest_iso: str | None) -> list[dict]:
    hours = age_hours(latest_iso)
    not_yet = "Not monitored yet"
    return [
        {"label": "API", "value": "Online" if api_ok else "Unreachable",
         "state": "ok" if api_ok else "bad"},
        {"label": "Database", "value": "Connected" if stats else "No response",
         "state": "ok" if stats else "bad"},
        {"label": "Latest stories stored", "value": freshness_label(hours),
         "state": freshness_state(hours)},
        {"label": "Breaking alerts sent", "value": str((stats or {}).get("alerts_sent", 0)),
         "state": "neutral"},
        {"label": "Collector", "value": not_yet, "state": "neutral"},
        {"label": "Scheduler", "value": not_yet, "state": "neutral"},
        {"label": "AI service", "value": not_yet, "state": "neutral"},
    ]


def build_real_checks(api_ok: bool, info: dict, now: datetime | None = None) -> list[dict]:
    """System checks from the /oracle/system answer. Only facts the API can prove."""
    latest = info.get("latest") or {}
    jobs = {j.get("job"): j for j in info.get("jobs") or []}
    cfg = info.get("configured") or {}

    def fresh(iso):
        hours = age_hours(iso, now)
        return freshness_label(hours), freshness_state(hours)

    story_label, story_state = fresh(latest.get("story"))
    article_label, article_state = fresh(latest.get("article"))

    last_runs = [j["last_run"] for j in jobs.values() if j.get("last_run")]
    if last_runs:
        sched_label, sched_state = fresh(max(last_runs))
    else:
        sched_label, sched_state = "No runs recorded yet", "neutral"

    digest = jobs.get("Digest")
    if digest is None:
        digest_value, digest_state = "No digest run recorded yet", "neutral"
    elif digest.get("last_ok"):
        label, digest_state = fresh(digest.get("last_success"))
        digest_value = f"OK, {label}"
    else:
        digest_value, digest_state = "Last run failed", "bad"

    def flag(on: bool, off_state: str):
        return ("Configured", "ok") if on else ("Not configured", off_state)

    email_value, email_state = flag(bool(cfg.get("email")), "warn")
    tg_value, tg_state = flag(bool(cfg.get("telegram")), "neutral")
    db_ok = bool((info.get("database") or {}).get("ok"))
    return [
        {"label": "API", "value": "Online" if api_ok else "Unreachable",
         "state": "ok" if api_ok else "bad"},
        {"label": "Database", "value": "Connected" if db_ok else "Not responding",
         "state": "ok" if db_ok else "bad"},
        {"label": "Latest stories stored", "value": story_label, "state": story_state},
        {"label": "Collector (last article)", "value": article_label, "state": article_state},
        {"label": "Scheduler (last job)", "value": sched_label, "state": sched_state},
        {"label": "Last digest", "value": digest_value, "state": digest_state},
        {"label": "AI service",
         "value": "API key configured" if cfg.get("ai") else "No API key",
         "state": "ok" if cfg.get("ai") else "bad"},
        {"label": "Email", "value": email_value, "state": email_state},
        {"label": "Telegram", "value": tg_value, "state": tg_state},
        {"label": "Breaking alerts sent", "value": str(info.get("alerts_total", 0)),
         "state": "neutral"},
    ]

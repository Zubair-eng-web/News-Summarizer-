"""Read-only analytics, status, alert history and source health from real database rows."""
import json
import re
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func, text

from app.collectors.rss import FEEDS
from app.collectors.youtube import CHANNELS
from app.core.category import categorize
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.models import AlertDB, ArticleDB, PipelineRunDB, StoryDB, VideoDB
from app.core.story import PRIORITIES, SENTIMENTS
from app.core.telegram_notifier import TelegramNotifier
from app.core import api_keys, source_health
from app.core.user_sources import _build, _rows

_WORD = re.compile(r"[a-z][a-z'-]{3,}")
_STOP = frozenset(
    "about after again against also amid and are been before being between both but can "
    "could did does doing down during each from further had has have having her here him "
    "his how into its just more most must not now off once only other our out over said "
    "says she should since some such than that the their them then there these they this "
    "those through under until very was were what when where which while who whom why will "
    "with would you your new".split()
)


def _open(factory=None):
    return (factory or SessionLocal)()


def _iso(value):
    return value.isoformat() if value else None


def _configured() -> dict:
    """Which services have credentials (booleans only, never the secrets)."""
    try:
        telegram = bool(TelegramNotifier.from_env().enabled)
    except Exception:
        telegram = False
    return {
        "ai": bool(settings.gemini_api_key) or bool(api_keys.load_db_keys()),
        "email": bool(
            (settings.email_sender and settings.email_password) or settings.resend_api_key
        ),
        "telegram": telegram,
    }


def _story_sources(row) -> set[str]:
    try:
        items = json.loads(row.sources_json or "[]")
    except ValueError:
        return set()
    if not isinstance(items, list):
        return set()
    return {i[0] for i in items if isinstance(i, list) and i and isinstance(i[0], str)}


def analytics(days: int = 30, factory=None, now: datetime | None = None) -> dict:
    if factory is None:
        init_db()
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=days)
    with _open(factory) as session:
        stories = session.query(StoryDB).filter(StoryDB.created_at >= cutoff).all()
        videos = session.query(VideoDB).filter(VideoDB.created_at >= cutoff).all()

    priority, sentiment, categories = Counter(), Counter(), Counter()
    day_all, day_crit, week_all, week_crit = Counter(), Counter(), Counter(), Counter()
    src_all, src_crit, terms = Counter(), Counter(), Counter()
    for row in stories:
        critical = row.priority == "Critical"
        day = row.created_at.strftime("%Y-%m-%d")
        week = (row.created_at - timedelta(days=row.created_at.weekday())).strftime("%Y-%m-%d")
        priority[row.priority] += 1
        sentiment[row.sentiment] += 1
        categories[categorize(row.title, row.summary or "")] += 1
        day_all[day] += 1
        week_all[week] += 1
        if critical:
            day_crit[day] += 1
            week_crit[week] += 1
        for name in _story_sources(row):
            src_all[name] += 1
            if critical:
                src_crit[name] += 1
        terms.update({w for w in _WORD.findall(row.title.lower()) if w not in _STOP})

    video_day = Counter(v.created_at.strftime("%Y-%m-%d") for v in videos)
    video_channel = Counter(v.channel for v in videos)
    return {
        "days": days,
        "total_stories": len(stories),
        "total_videos": len(videos),
        "priority": [{"priority": p, "stories": priority.get(p, 0)} for p in PRIORITIES],
        "sentiment": [{"sentiment": s, "stories": sentiment.get(s, 0)} for s in SENTIMENTS],
        "categories": [{"category": k, "stories": v} for k, v in categories.most_common()],
        "daily": [
            {"day": d, "stories": day_all[d], "critical": day_crit.get(d, 0)}
            for d in sorted(day_all)
        ],
        "weekly": [
            {"week": w, "stories": week_all[w], "critical": week_crit.get(w, 0)}
            for w in sorted(week_all)
        ],
        "sources": [
            {"source": k, "stories": v, "critical": src_crit.get(k, 0)}
            for k, v in src_all.most_common(15)
        ],
        "trending": [{"term": t, "count": c} for t, c in terms.most_common(10) if c >= 2],
        "video_daily": [{"day": d, "videos": video_day[d]} for d in sorted(video_day)],
        "video_channels": [{"channel": k, "videos": v} for k, v in video_channel.most_common()],
    }


def system_status(factory=None) -> dict:
    out = {
        "database": {"ok": False},
        "latest": {"story": None, "article": None, "video": None},
        "jobs": [],
        "recent_errors": [],
        "alerts_total": 0,
        "configured": _configured(),
        "demo_mode": settings.demo_mode,
        "debug": settings.debug,
    }
    try:
        if factory is None:
            init_db()
        with _open(factory) as session:
            session.execute(text("select 1"))
            out["latest"] = {
                "story": _iso(session.query(func.max(StoryDB.created_at)).scalar()),
                "article": _iso(session.query(func.max(ArticleDB.collected_at)).scalar()),
                "video": _iso(session.query(func.max(VideoDB.created_at)).scalar()),
            }
            out["alerts_total"] = session.query(AlertDB).count()
            runs = (
                session.query(PipelineRunDB)
                .order_by(PipelineRunDB.started_at.desc(), PipelineRunDB.id.desc())
                .limit(500)
                .all()
            )
        jobs: dict[str, dict] = {}
        for r in runs:
            job = jobs.setdefault(
                r.job,
                {"job": r.job, "last_run": _iso(r.started_at), "last_ok": bool(r.ok),
                 "last_success": None, "runs": 0},
            )
            job["runs"] += 1
            if r.ok and job["last_success"] is None:
                job["last_success"] = _iso(r.started_at)
        out["jobs"] = list(jobs.values())
        out["recent_errors"] = [
            {"job": r.job, "at": _iso(r.started_at), "error": r.error}
            for r in runs
            if not r.ok
        ][:5]
        out["database"]["ok"] = True
    except Exception:
        out["database"]["ok"] = False
    return out


def alert_history(limit: int = 50, factory=None, now: datetime | None = None) -> dict:
    if factory is None:
        init_db()
    now = now or datetime.utcnow()
    with _open(factory) as session:
        total = session.query(AlertDB).count()
        recent = session.query(AlertDB).filter(AlertDB.sent_at >= now - timedelta(hours=24)).count()
        rows = (
            session.query(AlertDB)
            .order_by(AlertDB.sent_at.desc(), AlertDB.id.desc())
            .limit(limit)
            .all()
        )
        alerts = [{"title": r.title, "sent_at": _iso(r.sent_at)} for r in rows]
    return {"total": total, "last_24h": recent, "alerts": alerts, "configured": _configured()}


def recent_runs(limit: int = 30, factory=None) -> list[dict]:
    if factory is None:
        init_db()
    with _open(factory) as session:
        rows = (
            session.query(PipelineRunDB)
            .order_by(PipelineRunDB.started_at.desc(), PipelineRunDB.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "job": r.job,
                "ok": bool(r.ok),
                "started_at": _iso(r.started_at),
                "duration_ms": r.duration_ms,
                "error": r.error,
                "detail": r.detail,
            }
            for r in rows
        ]


def _source_state(last: datetime | None, now: datetime) -> str:
    if last is None:
        return "no_data"
    hours = (now - last).total_seconds() / 3600
    return "active" if hours <= 48 else "stale" if hours <= 168 else "no_recent"


def source_status(factory=None, now: datetime | None = None) -> dict:
    """Every monitored RSS feed and YouTube channel with real stored counts and last time."""
    if factory is None:
        init_db()
    now = now or datetime.utcnow()
    try:
        custom_feeds = _build(_rows("rss", factory), lambda url: True)
        custom_channels = _build(_rows("youtube", factory), lambda url: True)
    except Exception:
        custom_feeds, custom_channels = {}, {}
    with _open(factory) as session:
        articles = {
            r[0]: (r[1], r[2])
            for r in session.query(
                ArticleDB.source, func.count(ArticleDB.id), func.max(ArticleDB.collected_at)
            ).group_by(ArticleDB.source).all()
        }
        videos = {
            r[0]: (r[1], r[2])
            for r in session.query(
                VideoDB.channel, func.count(VideoDB.id), func.max(VideoDB.created_at)
            ).group_by(VideoDB.channel).all()
        }
    try:
        health = source_health.load_all(factory)
    except Exception:
        health = {}
    planned = (
        [("rss", n, True, articles) for n in FEEDS]
        + [("rss", n, False, articles) for n in custom_feeds]
        + [("youtube", n, True, videos) for n in CHANNELS]
        + [("youtube", n, False, videos) for n in custom_channels]
    )
    rows = []
    for kind, name, builtin, found in planned:
        count, last = found.get(name, (0, None))
        h = health.get(name, {})
        rows.append(
            {
                "name": name,
                "kind": kind,
                "builtin": builtin,
                "items": count,
                "last_at": _iso(last),
                "status": _source_state(last, now),
                "last_checked": h.get("last_checked"),
                "last_items": h.get("last_items"),
                "last_error": h.get("last_error", ""),
            }
        )
    return {"total": len(rows), "sources": rows}
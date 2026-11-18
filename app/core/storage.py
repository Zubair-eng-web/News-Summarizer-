import json
from datetime import datetime, timedelta

from sqlalchemy import func

from app.collectors.rss import Article
from app.core.category import categorize
from app.core.database import SessionLocal, init_db
from app.core.models import AlertDB, ArticleDB, DigestedDB, SettingDB, StoryDB, VideoDB
from app.core.story import PRIORITIES, Story
from app.core.video import VideoSummary


def save_new_articles(articles: list[Article]) -> list[Article]:
    """DB me sirf naye articles save karta hai, aur wahi return karta hai."""
    init_db()
    new_articles: list[Article] = []

    with SessionLocal() as session:
        existing_links = {row[0] for row in session.query(ArticleDB.link).all()}

        for a in articles:
            if a.link in existing_links:
                continue
            session.add(
                ArticleDB(
                    title=a.title[:500],
                    link=a.link,
                    summary=a.summary,
                    source=a.source[:100],
                    image_url=(getattr(a, "extra", None) or {}).get("image", "")[:1000],
                    published=a.published,
                )
            )
            existing_links.add(a.link)
            new_articles.append(a)

        session.commit()

    return new_articles


def count_articles() -> int:
    init_db()
    with SessionLocal() as session:
        return session.query(ArticleDB).count()


def get_undigested_articles(hours: int = 36) -> list[Article]:
    """Pichle `hours` ghanton ke wo articles jo abhi tak kisi digest me nahi gaye."""
    init_db()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with SessionLocal() as session:
        done = {row[0] for row in session.query(DigestedDB.link).all()}
        rows = (
            session.query(ArticleDB)
            .filter(ArticleDB.collected_at >= cutoff)
            .order_by(ArticleDB.collected_at.desc())
            .all()
        )
        return [
            Article(
                title=r.title,
                link=r.link,
                summary=r.summary or "",
                source=r.source,
                published=r.published,
                extra={"image": r.image_url} if r.image_url else {},
            )
            for r in rows
            if r.link not in done
        ]


def mark_digested(articles: list[Article]) -> None:
    """Articles ko 'digest me chala gaya' likh deta hai."""
    if not articles:
        return
    init_db()
    with SessionLocal() as session:
        existing = {row[0] for row in session.query(DigestedDB.link).all()}
        for a in articles:
            link = a.link[:1000]
            if link in existing:
                continue
            session.add(DigestedDB(link=link))
            existing.add(link)
        session.commit()


def story_key(story: Story) -> str:
    """Story ki pehchan: us ka pehla source link."""
    key = story.sources[0][1] if story.sources else story.title
    return key[:1000]


def filter_unalerted(stories: list[Story]) -> list[Story]:
    """Sirf wo stories jin ka alert pehle nahi gaya."""
    if not stories:
        return []
    init_db()
    with SessionLocal() as session:
        done = {row[0] for row in session.query(AlertDB.story_key).all()}
    return [s for s in stories if story_key(s) not in done]


def mark_alerted(stories: list[Story]) -> None:
    """Stories ko 'alert bhej diya' likh deta hai."""
    if not stories:
        return
    init_db()
    with SessionLocal() as session:
        existing = {row[0] for row in session.query(AlertDB.story_key).all()}
        for s in stories:
            key = story_key(s)
            if key in existing:
                continue
            session.add(AlertDB(story_key=key, title=s.title[:500]))
            existing.add(key)
        session.commit()


def _recent_story_keys(session, days: int = 7) -> set[str]:
    """Keys (first source link, else title) of stories saved in the last `days` days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    keys: set[str] = set()
    for sources_json, title in (
        session.query(StoryDB.sources_json, StoryDB.title).filter(StoryDB.created_at >= cutoff).all()
    ):
        try:
            sources = json.loads(sources_json or "[]")
        except ValueError:
            sources = []
        if sources and len(sources[0]) == 2 and sources[0][1]:
            keys.add(sources[0][1][:1000])
        else:
            keys.add((title or "")[:1000])
    return keys


def save_stories(stories: list[Story]) -> None:
    """Digest ki stories DB me save karta hai (API aur dashboard ke liye)."""
    if not stories:
        return
    init_db()
    now = datetime.utcnow()  # ek digest ki saari stories ka ek hi waqt
    with SessionLocal() as session:
        known = _recent_story_keys(session)
        for s in stories:  # rank ke order me save hoti hain, is liye id se order milta hai
            key = story_key(s)
            if key in known:  # same story pehle kisi digest me save ho chuki hai
                continue
            known.add(key)
            session.add(
                StoryDB(
                    title=s.title[:500],
                    summary=s.summary,
                    priority=s.priority,
                    sentiment=s.sentiment,
                    credibility=s.credibility,
                    claims_json=json.dumps(getattr(s, "claims", None) or []),
                    image_url=(getattr(s, "image_url", "") or "")[:1000],
                    sources_json=json.dumps([list(x) for x in s.sources]),
                    created_at=now,
                )
            )
        session.commit()


def _story_to_dict(row: StoryDB) -> dict:
    try:
        sources = json.loads(row.sources_json or "[]")
    except ValueError:
        sources = []
    try:
        claims = json.loads(getattr(row, "claims_json", None) or "[]")
    except ValueError:
        claims = []
    if not isinstance(claims, list):
        claims = []
    return {
        "id": row.id,
        "title": row.title,
        "summary": row.summary,
        "priority": row.priority,
        "sentiment": row.sentiment,
        "credibility": row.credibility,
        "claims": claims,
        "image_url": getattr(row, "image_url", "") or "",
        "category": categorize(row.title, row.summary or ""),
        "sources": [{"source": s[0], "link": s[1]} for s in sources if len(s) == 2],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def get_recent_stories(
    limit: int = 20, priority: str | None = None, hours: int | None = None
) -> list[dict]:
    """Sab se naya digest pehle, aur digest ke andar rank ke order me."""
    init_db()
    with SessionLocal() as session:
        query = session.query(StoryDB)
        if priority:
            query = query.filter(StoryDB.priority == priority)
        if hours:
            query = query.filter(StoryDB.created_at >= datetime.utcnow() - timedelta(hours=hours))
        rows = query.order_by(StoryDB.created_at.desc(), StoryDB.id.asc()).limit(limit).all()
        return [_story_to_dict(r) for r in rows]


def get_recent_articles(limit: int = 50) -> list[dict]:
    init_db()
    with SessionLocal() as session:
        rows = session.query(ArticleDB).order_by(ArticleDB.collected_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "link": r.link,
                "source": r.source,
                "published": r.published.isoformat() if r.published else None,
                "collected_at": r.collected_at.isoformat() if r.collected_at else None,
            }
            for r in rows
        ]


def get_stats() -> dict:
    init_db()
    with SessionLocal() as session:
        by_priority = {p: 0 for p in PRIORITIES}
        for priority, n in (
            session.query(StoryDB.priority, func.count(StoryDB.id)).group_by(StoryDB.priority).all()
        ):
            by_priority[priority] = n
        return {
            "articles": session.query(ArticleDB).count(),
            "stories": session.query(StoryDB).count(),
            "alerts_sent": session.query(AlertDB).count(),
            "stories_by_priority": by_priority,
        }


def get_known_video_ids() -> set[str]:
    """Jin videos ki summary pehle ban chuki hai."""
    init_db()
    with SessionLocal() as session:
        return {row[0] for row in session.query(VideoDB.video_id).all()}


def save_videos(videos: list[VideoSummary]) -> None:
    """Video summaries save karta hai (pehle se maujood video dobara save nahi hoti)."""
    if not videos:
        return
    init_db()
    with SessionLocal() as session:
        existing = {row[0] for row in session.query(VideoDB.video_id).all()}
        for v in videos:
            if v.video_id in existing:
                continue
            session.add(
                VideoDB(
                    video_id=v.video_id,
                    title=v.title[:500],
                    link=v.link[:1000],
                    channel=v.channel[:100],
                    published=v.published,
                    summary=v.summary,
                    key_points_json=json.dumps(v.key_points),
                    takeaway=v.takeaway,
                    has_transcript=v.has_transcript,
                )
            )
            existing.add(v.video_id)
        session.commit()


def get_recent_videos(limit: int = 10, hours: int | None = None) -> list[dict]:
    init_db()
    with SessionLocal() as session:
        query = session.query(VideoDB)
        if hours:
            query = query.filter(VideoDB.created_at >= datetime.utcnow() - timedelta(hours=hours))
        rows = query.order_by(VideoDB.published.desc().nulls_last(), VideoDB.id.desc()).limit(limit).all()
        result = []
        for r in rows:
            try:
                points = json.loads(r.key_points_json or "[]")
            except ValueError:
                points = []
            result.append(
                {
                    "video_id": r.video_id,
                    "title": r.title,
                    "link": r.link,
                    "channel": r.channel,
                    "published": r.published.isoformat() if r.published else None,
                    "summary": r.summary,
                    "key_points": points,
                    "takeaway": r.takeaway,
                    "has_transcript": bool(r.has_transcript),
                }
            )
        return result


def get_stories_between(start: datetime, end: datetime) -> list[dict]:
    """Wo stories jin ka digest [start, end) me bana, naye pehle."""
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(StoryDB)
            .filter(StoryDB.created_at >= start, StoryDB.created_at < end)
            .order_by(StoryDB.created_at.desc(), StoryDB.id.asc())
            .all()
        )
        return [_story_to_dict(r) for r in rows]


def _video_to_dict(r: VideoDB) -> dict:
    try:
        points = json.loads(r.key_points_json or "[]")
    except ValueError:
        points = []
    return {
        "video_id": r.video_id,
        "title": r.title,
        "link": r.link,
        "channel": r.channel,
        "published": r.published.isoformat() if r.published else None,
        "summary": r.summary,
        "key_points": points,
        "takeaway": r.takeaway,
        "has_transcript": bool(r.has_transcript),
    }


def get_videos_between(start: datetime, end: datetime) -> list[dict]:
    """Wo videos jin ki summary [start, end) me bani, naye pehle."""
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(VideoDB)
            .filter(VideoDB.created_at >= start, VideoDB.created_at < end)
            .order_by(VideoDB.published.desc().nulls_last(), VideoDB.id.desc())
            .all()
        )
        return [_video_to_dict(r) for r in rows]


def get_setting(key: str) -> str | None:
    """Saved setting ki value, ya None agar kabhi save nahi hui."""
    init_db()
    with SessionLocal() as session:
        row = session.get(SettingDB, key)
        return row.value if row else None


def set_setting(key: str, value: str) -> None:
    init_db()
    with SessionLocal() as session:
        row = session.get(SettingDB, key)
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            session.add(SettingDB(key=key, value=value))
        session.commit()

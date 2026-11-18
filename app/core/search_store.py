from app.core.database import SessionLocal, init_db
from app.core.models import ArticleDB


def get_articles_with_summary(limit: int = 300) -> list[dict]:
    """Research chat ke liye articles (summary ke saath), naye pehle."""
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(ArticleDB)
            .order_by(ArticleDB.collected_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "title": r.title,
                "link": r.link,
                "source": r.source,
                "summary": r.summary or "",
            }
            for r in rows
        ]

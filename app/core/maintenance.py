"""Data retention (purana data saaf karna) aur SQLite database backup."""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import DATABASE_URL, SessionLocal, init_db
from app.core.models import ArticleDB, DigestedDB, EmbeddingDB


def cleanup_old_data(days: int | None = None, session_factory=None, now=None) -> dict:
    """Articles, digested records aur embeddings jo `days` se purane hain, delete karta hai.

    Stories, videos aur alerts rehte hain (weekly report aur alert dedup unpar chalte hain).
    days <= 0 ho to cleanup band hai.
    """
    days = settings.retention_days if days is None else days
    if days <= 0:
        return {"articles": 0, "digested": 0, "embeddings": 0}
    if session_factory is None:
        init_db()
    cutoff = (now or datetime.utcnow()) - timedelta(days=days)
    with (session_factory or SessionLocal)() as db:
        counts = {
            "articles": db.query(ArticleDB)
            .filter(ArticleDB.collected_at < cutoff)
            .delete(synchronize_session=False),
            "digested": db.query(DigestedDB)
            .filter(DigestedDB.digested_at < cutoff)
            .delete(synchronize_session=False),
            "embeddings": db.query(EmbeddingDB)
            .filter(EmbeddingDB.created_at < cutoff)
            .delete(synchronize_session=False),
        }
        db.commit()
    return counts


def backup_sqlite(url: str | None = None, dest_dir="backups", keep: int = 7, now=None) -> Path:
    """SQLite ka consistent backup (chalte database par bhi safe). Sirf aakhri `keep` rakhta hai."""
    parsed = make_url(url or DATABASE_URL)
    if parsed.get_backend_name() != "sqlite":
        raise ValueError("Ye command sirf SQLite ke liye hai. PostgreSQL ke liye pg_dump use karein")
    if not parsed.database or parsed.database == ":memory:":
        raise ValueError("In-memory database ka backup nahi ho sakta")
    source_path = Path(parsed.database)
    if not source_path.exists():
        raise FileNotFoundError(f"Database file nahi mili: {source_path}")

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.utcnow()).strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{source_path.stem}-{stamp}.db"

    source = sqlite3.connect(str(source_path))
    target = sqlite3.connect(str(dest))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    backups = sorted(dest_dir.glob(f"{source_path.stem}-*.db"))
    for old in backups[: max(len(backups) - max(keep, 1), 0)]:
        old.unlink()
    return dest


if __name__ == "__main__":
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "cleanup":
        print("Cleanup:", cleanup_old_data())
    elif command == "backup":
        print("Backup saved:", backup_sqlite())
    else:
        print("Use: python -m app.core.maintenance cleanup|backup")
        raise SystemExit(2)
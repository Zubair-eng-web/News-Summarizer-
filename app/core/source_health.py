"""Last collection result per source. Recording never raises, so it can never break a job."""
from datetime import datetime

from app.core.database import SessionLocal, init_db
from app.core.models import SourceHealthDB


def record(name: str, kind: str, ok: bool, items: int = 0, error: str = "", factory=None) -> None:
    try:
        if factory is None:
            init_db()
        with (factory or SessionLocal)() as session:
            now = datetime.utcnow()
            row = session.get(SourceHealthDB, name[:100])
            if row is None:
                row = SourceHealthDB(name=name[:100], kind=kind)
                session.add(row)
            row.kind = kind
            row.last_checked_at = now
            row.last_items = items
            row.last_error = "" if ok else (error or "")[:300]
            if ok:
                row.last_ok_at = now
            session.commit()
    except Exception:
        pass


def load_all(factory=None) -> dict[str, dict]:
    with (factory or SessionLocal)() as session:
        return {
            r.name: {
                "last_checked": r.last_checked_at.isoformat() if r.last_checked_at else None,
                "last_ok": r.last_ok_at.isoformat() if r.last_ok_at else None,
                "last_items": r.last_items,
                "last_error": r.last_error,
            }
            for r in session.query(SourceHealthDB).all()
        }
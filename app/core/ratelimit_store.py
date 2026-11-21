"""Rate limiter jo database mein hits rakhta hai, taake restart par reset na ho."""
import time

from sqlalchemy import text

from app.core.database import SessionLocal

_calls = 0


def _ensure(db) -> None:
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS rate_hits (bucket VARCHAR(300) NOT NULL, ts FLOAT NOT NULL)"
    ))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_rate_hits_bucket_ts ON rate_hits (bucket, ts)"))


def hit(key: str, limit: int, window: float, session_factory=None, clock=time.time) -> float:
    """0 = allowed, warna kitne seconds baad dobara try karein."""
    global _calls
    bucket = f"{limit}:{window}:{key}"[:300]
    now = clock()
    cutoff = now - window
    with (session_factory or SessionLocal)() as db:
        _ensure(db)
        db.execute(text("DELETE FROM rate_hits WHERE bucket = :b AND ts <= :c"), {"b": bucket, "c": cutoff})
        _calls += 1
        if _calls % 50 == 0:
            db.execute(text("DELETE FROM rate_hits WHERE ts <= :c"), {"c": now - 86400})
        rows = db.execute(
            text("SELECT ts FROM rate_hits WHERE bucket = :b ORDER BY ts"), {"b": bucket}
        ).all()
        if len(rows) >= limit:
            db.commit()
            return max(rows[0][0] + window - now, 0.001)
        db.execute(text("INSERT INTO rate_hits (bucket, ts) VALUES (:b, :t)"), {"b": bucket, "t": now})
        db.commit()
        return 0.0

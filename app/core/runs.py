"""Pipeline run history: every scheduler, API or CLI job is recorded here."""
import os
import time
from datetime import datetime

from app.core.database import SessionLocal, init_db
from app.core.models import PipelineRunDB


def record(
    job: str,
    ok: bool,
    started_at: datetime,
    duration_ms: float,
    detail: str = "",
    error: str = "",
    factory=None,
) -> None:
    """Save one run. Never raises, so history problems can never break a job."""
    if factory is None and os.getenv("PYTEST_CURRENT_TEST"):
        return  # tests must not write into the real database
    try:
        if factory is None:
            init_db()
        with (factory or SessionLocal)() as session:
            session.add(
                PipelineRunDB(
                    job=job[:50],
                    ok=ok,
                    started_at=started_at,
                    duration_ms=int(duration_ms),
                    detail=detail[:2000],
                    error=error[:300],
                )
            )
            session.commit()
    except Exception as e:
        print(f"[WARN] Run history save nahi hui: {type(e).__name__}")


def _detail(result) -> str:
    if isinstance(result, dict) and result.get("trace"):
        return "\n".join(str(line) for line in result["trace"])
    return ""


def track(job: str, fn):
    """Run fn(), record how it went, and return its result (errors are re-raised)."""
    started = datetime.utcnow()
    t0 = time.perf_counter()
    try:
        result = fn()
    except Exception as e:
        message = " ".join(str(e).split())[:200]
        record(job, False, started, (time.perf_counter() - t0) * 1000,
               error=f"{type(e).__name__}: {message}")
        raise
    record(job, True, started, (time.perf_counter() - t0) * 1000, detail=_detail(result))
    return result
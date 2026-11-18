"""Read-only ORACLE endpoints: analytics, system status, alert history, run history, sources."""
from fastapi import APIRouter, Query

from app.core import oracle_stats

router = APIRouter(prefix="/oracle", tags=["oracle"])


@router.get("/analytics")
def analytics(days: int = Query(30, ge=1, le=365)):
    return oracle_stats.analytics(days)


@router.get("/system")
def system():
    return oracle_stats.system_status()


@router.get("/alerts")
def alerts(limit: int = Query(50, ge=1, le=200)):
    return oracle_stats.alert_history(limit)


@router.get("/runs")
def runs(limit: int = Query(30, ge=1, le=200)):
    items = oracle_stats.recent_runs(limit)
    return {"count": len(items), "runs": items}


@router.get("/sources")
def sources():
    return oracle_stats.source_status()
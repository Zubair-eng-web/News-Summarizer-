"""Related articles and videos endpoint (read-only, no LLM call, so no Gemini quota)."""
from fastapi import APIRouter, Query

from app.agents.related import related_content

router = APIRouter(tags=["related"])


@router.get("/related")
def related(q: str = Query(..., min_length=2, max_length=300)):
    return related_content(q)
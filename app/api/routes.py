from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.deep_research import run_research
from app.agents.research_web import add_web_sources
from app.agents.research import ResearchError, answer_question
from app.core.storage import (
    get_recent_articles,
    get_recent_stories,
    get_recent_videos,
    get_stats,
)
from app.core.interests import get_interests, save_interests
from app.core.maintenance import cleanup_old_data
from app.core.story import PRIORITIES
from app.scheduler import (
    is_busy,
    run_alerts,
    run_digest,
    run_user_digests,
    run_videos,
    run_weekly,
    safe_run,
)
from app.weekly import build_weekly_report

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@router.get("/stories")
def list_stories(
    limit: int = Query(20, ge=1, le=100),
    priority: str | None = None,
    hours: int | None = Query(None, ge=1, le=24 * 365),
):
    if priority is not None:
        priority = priority.strip().capitalize()
        if priority not in PRIORITIES:
            raise HTTPException(
                status_code=400, detail=f"priority in me se ho: {', '.join(PRIORITIES)}"
            )
    stories = get_recent_stories(limit=limit, priority=priority, hours=hours)
    return {"count": len(stories), "stories": stories}


@router.get("/articles")
def list_articles(limit: int = Query(50, ge=1, le=200)):
    articles = get_recent_articles(limit=limit)
    return {"count": len(articles), "articles": articles}


@router.get("/stats")
def stats():
    return get_stats()


@router.get("/videos")
def list_videos(limit: int = Query(10, ge=1, le=50)):
    videos = get_recent_videos(limit=limit)
    return {"count": len(videos), "videos": videos}


@router.post("/chat")
def chat(req: ChatRequest):
    """Collected khabron se sawal ka jawab (sources ke saath)."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Sawal khali nahi ho sakta")
    try:
        return answer_question(question)
    except ValueError as e:  # GEMINI_API_KEY set nahi
        raise HTTPException(status_code=503, detail=str(e))
    except ResearchError as e:
        raise HTTPException(status_code=502, detail=str(e))


def _start(job, name: str, background_tasks: BackgroundTasks) -> dict:
    if is_busy():
        raise HTTPException(
            status_code=409, detail="Dusra job abhi chal raha hai, thori der baad try karein"
        )
    background_tasks.add_task(safe_run, job, name)
    return {"status": "started", "job": name}


@router.post("/run-digest")
def trigger_digest(background_tasks: BackgroundTasks):
    """Digest background me chalata hai (naye articles hon to email bhi jati hai)."""
    return _start(run_digest, "Digest", background_tasks)


@router.post("/run-alerts")
def trigger_alerts(background_tasks: BackgroundTasks):
    """Breaking alert check background me chalata hai."""
    return _start(run_alerts, "Alert check", background_tasks)


@router.post("/run-videos")
def trigger_videos(background_tasks: BackgroundTasks):
    """YouTube videos ki summaries background me banata hai."""
    return _start(run_videos, "Videos", background_tasks)


@router.get("/weekly")
def weekly(overview: bool = False):
    """Weekly report (JSON). overview=true par Gemini se khulasa bhi banta hai."""
    return build_weekly_report(overview=overview)


@router.post("/run-weekly")
def trigger_weekly(background_tasks: BackgroundTasks):
    """Weekly report banakar email karta hai (background me)."""
    return _start(run_weekly, "Weekly report", background_tasks)


class InterestsRequest(BaseModel):
    interests: str = Field(default="", max_length=1000)


@router.get("/interests")
def read_interests():
    """Personalization keywords jo ranking me use hoti hain."""
    return {"interests": get_interests()}


@router.put("/interests")
def update_interests(req: InterestsRequest):
    """Keywords save karta hai (comma se alag). Khali bhejne par personalization band."""
    return {"interests": save_interests(req.interests)}


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)


@router.post("/research")
def research(req: ResearchRequest):
    """Topic par multi-step report (collected khabron se, sources ke saath)."""
    topic = req.topic.strip()
    if len(topic) < 3:
        raise HTTPException(status_code=400, detail="Topic bohat chhota hai")
    try:
        return add_web_sources(run_research(topic), topic)
    except ValueError as e:  # GEMINI_API_KEY set nahi
        raise HTTPException(status_code=503, detail=str(e))
    except ResearchError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/run-cleanup")
def trigger_cleanup(background_tasks: BackgroundTasks):
    """Purana data (retention) background me saaf karta hai."""
    return _start(cleanup_old_data, "Cleanup", background_tasks)


@router.post("/run-user-digests")
def trigger_user_digests(background_tasks: BackgroundTasks):
    """Opted-in users ko unke apne waqt ki digest background me bhejta hai."""
    return _start(run_user_digests, "User digests", background_tasks)

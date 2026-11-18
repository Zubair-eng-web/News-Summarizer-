"""Public demo ke liye sample data (asli khabrein nahi, sirf namoona).

Chalane ka tareeqa:
    python -m scripts.seed_demo          # sirf tab jab stories table khali ho
    python -m scripts.seed_demo --force  # purana demo data hata kar dobara daalo
"""
import json
import sys
from datetime import datetime, timedelta

DEMO_HOST = "demo.example.com"
DEMO_SOURCE = "Demo News"

STORIES = [
    {
        "title": "Demo: Major earthquake drill held across coastal cities",
        "summary": "Authorities ran a large emergency drill in several coastal cities. Officials say response times improved compared with last year.",
        "priority": "Critical",
        "sentiment": "neutral",
        "credibility": "Confirmed by 3 sources",
        "claims": [
            {"claim": "Drill covered five cities", "supported_by": ["Demo News", "Demo Times"], "contradicted_by": [], "status": "confirmed"},
        ],
    },
    {
        "title": "Demo: Central bank holds interest rate steady",
        "summary": "The central bank kept its policy rate unchanged and said inflation is easing slowly.",
        "priority": "High",
        "sentiment": "neutral",
        "credibility": "Confirmed by 2 sources",
        "claims": [
            {"claim": "Rate unchanged", "supported_by": ["Demo News", "Demo Business"], "contradicted_by": [], "status": "confirmed"},
            {"claim": "Inflation below 8 percent", "supported_by": ["Demo News"], "contradicted_by": ["Demo Business"], "status": "disputed"},
        ],
    },
    {
        "title": "Demo: New open-source AI toolkit released by university lab",
        "summary": "A university lab released a free toolkit that makes it easier to evaluate language models.",
        "priority": "High",
        "sentiment": "positive",
        "credibility": "Single source",
        "claims": [],
    },
    {
        "title": "Demo: City council approves new bike lanes",
        "summary": "The council approved a plan for protected bike lanes on three main roads, starting next spring.",
        "priority": "Medium",
        "sentiment": "positive",
        "credibility": "Single source",
        "claims": [],
    },
    {
        "title": "Demo: Cricket team announces squad for upcoming series",
        "summary": "The board announced a 15-member squad, with two new faces in the batting line-up.",
        "priority": "Medium",
        "sentiment": "neutral",
        "credibility": "Confirmed by 2 sources",
        "claims": [],
    },
    {
        "title": "Demo: Local food festival returns this weekend",
        "summary": "The annual food festival opens on Saturday with over 60 stalls.",
        "priority": "Low",
        "sentiment": "positive",
        "credibility": "Single source",
        "claims": [],
    },
]

VIDEOS = [
    {
        "video_id": "demo-video-1",
        "title": "Demo: Weekly economy explained in 5 minutes",
        "channel": "Demo Channel",
        "summary": "A short explainer on inflation, interest rates and what they mean for households.",
        "key_points": ["Inflation is easing slowly", "Rates were held steady", "Savings returns remain modest"],
        "takeaway": "Expect stable rates in the near term.",
        "has_transcript": True,
    },
    {
        "video_id": "demo-video-2",
        "title": "Demo: How emergency drills save lives",
        "channel": "Demo Channel",
        "summary": "Experts explain why regular drills shorten response times.",
        "key_points": ["Practice builds habits", "Clear signage matters"],
        "takeaway": "Take part in local drills when you can.",
        "has_transcript": False,
    },
]


def seed(session_factory=None, force: bool = False) -> dict:
    """Sample stories, articles aur videos daalta hai. session_factory tests ke liye hai."""
    from app.core.models import ArticleDB, StoryDB, VideoDB

    if session_factory is None:
        from app.core.database import SessionLocal, init_db

        init_db()
        session_factory = SessionLocal

    now = datetime.utcnow()
    with session_factory() as session:
        if force:
            session.query(StoryDB).filter(StoryDB.sources_json.like(f"%{DEMO_HOST}%")).delete(
                synchronize_session=False
            )
            session.query(ArticleDB).filter(ArticleDB.link.like(f"%{DEMO_HOST}%")).delete(
                synchronize_session=False
            )
            session.query(VideoDB).filter(VideoDB.video_id.like("demo-video-%")).delete(
                synchronize_session=False
            )
            session.commit()
        elif session.query(StoryDB).count():
            return {"seeded": False, "reason": "stories pehle se maujood hain (--force se dobara)"}

        # stories rank ke order me, ek hi created_at ke saath (app ka apna pattern)
        for i, s in enumerate(STORIES, 1):
            link = f"https://{DEMO_HOST}/story/{i}"
            session.add(
                StoryDB(
                    title=s["title"][:500],
                    summary=s["summary"],
                    priority=s["priority"],
                    sentiment=s["sentiment"],
                    credibility=s["credibility"],
                    claims_json=json.dumps(s["claims"]),
                    sources_json=json.dumps([[DEMO_SOURCE, link]]),
                    created_at=now,
                )
            )
            session.add(
                ArticleDB(
                    title=s["title"][:500],
                    link=link,
                    summary=s["summary"],
                    source=DEMO_SOURCE,
                    published=now - timedelta(hours=i),
                    collected_at=now,
                )
            )
        for i, v in enumerate(VIDEOS, 1):
            session.add(
                VideoDB(
                    video_id=v["video_id"],
                    title=v["title"],
                    link=f"https://{DEMO_HOST}/video/{i}",
                    channel=v["channel"],
                    published=now - timedelta(hours=6 * i),
                    summary=v["summary"],
                    key_points_json=json.dumps(v["key_points"]),
                    takeaway=v["takeaway"],
                    has_transcript=v["has_transcript"],
                    created_at=now,
                )
            )
        session.commit()
    return {"seeded": True, "stories": len(STORIES), "videos": len(VIDEOS)}


def main(argv=None) -> None:
    args = sys.argv[1:] if argv is None else argv
    print(json.dumps(seed(force="--force" in args), ensure_ascii=False))


if __name__ == "__main__":
    main()
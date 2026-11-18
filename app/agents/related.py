"""Related articles and videos for a chat question (keyword search only, no LLM call)."""
from app.agents.research import Doc, load_documents, retrieve
from app.core.storage import get_recent_videos

MIN_SCORE = 0.1


def related_content(
    query: str,
    docs: list[Doc] | None = None,
    videos: list[dict] | None = None,
    k_articles: int = 4,
    k_videos: int = 3,
) -> dict:
    query = (query or "").strip()
    if not query:
        return {"query": query, "articles": [], "videos": []}
    docs = docs if docs is not None else load_documents()
    videos = videos if videos is not None else get_recent_videos(limit=100)

    articles = [
        {
            "title": d.title,
            "kind": d.kind,
            "score": round(score, 3),
            "sources": [{"source": s, "link": link} for s, link in d.sources],
        }
        for d, score in retrieve(query, docs, k=k_articles, min_score=MIN_SCORE)
    ]

    video_docs = [
        Doc(
            title=v.get("title", ""),
            text=f"{v.get('title', '')}. {v.get('summary', '')}",
            sources=[(v.get("channel", ""), v.get("link", ""))],
            kind="video",
        )
        for v in videos
    ]
    by_doc = {id(d): v for d, v in zip(video_docs, videos)}
    found = []
    for d, score in retrieve(query, video_docs, k=k_videos, min_score=MIN_SCORE):
        v = by_doc[id(d)]
        found.append(
            {
                "title": v.get("title", ""),
                "channel": v.get("channel", ""),
                "link": v.get("link", ""),
                "video_id": v.get("video_id", ""),
                "score": round(score, 3),
            }
        )
    return {"query": query, "articles": articles, "videos": found}
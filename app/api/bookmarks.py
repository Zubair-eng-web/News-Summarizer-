"""Bookmark endpoints (login required, same bearer token as the other /me routes)."""
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.core import bookmarks

router = APIRouter(tags=["bookmarks"])


@router.get("/me/bookmarks")
def list_my_bookmarks(user: dict = Depends(get_current_user)):
    stories = bookmarks.list_bookmarked_stories(user["id"])
    return {
        "count": len(stories),
        "limit": bookmarks.MAX_PER_USER,
        "story_ids": [s["id"] for s in stories],
        "stories": stories,
    }


@router.put("/me/bookmarks/{story_id}")
def save_bookmark(story_id: int, user: dict = Depends(get_current_user)):
    try:
        created = bookmarks.add_bookmark(user["id"], story_id)
    except bookmarks.StoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except bookmarks.BookmarkLimitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"story_id": story_id, "saved": True, "created": created}


@router.delete("/me/bookmarks/{story_id}")
def delete_bookmark(story_id: int, user: dict = Depends(get_current_user)):
    if not bookmarks.remove_bookmark(user["id"], story_id):
        raise HTTPException(status_code=404, detail="Bookmark nahi mila")
    return {"story_id": story_id, "saved": False}
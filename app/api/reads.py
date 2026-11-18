"""Read/unread endpoints (login required, same bearer token as the other /me routes)."""
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.core import reads

router = APIRouter(tags=["reads"])


@router.get("/me/reads")
def list_my_reads(user: dict = Depends(get_current_user)):
    ids = reads.list_read_ids(user["id"])
    return {"count": len(ids), "story_ids": ids}


@router.put("/me/reads/{story_id}")
def mark_story_read(story_id: int, user: dict = Depends(get_current_user)):
    try:
        created = reads.mark_read(user["id"], story_id)
    except reads.StoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"story_id": story_id, "read": True, "created": created}


@router.delete("/me/reads/{story_id}")
def mark_story_unread(story_id: int, user: dict = Depends(get_current_user)):
    if not reads.mark_unread(user["id"], story_id):
        raise HTTPException(status_code=404, detail="Story read nahi thi")
    return {"story_id": story_id, "read": False}
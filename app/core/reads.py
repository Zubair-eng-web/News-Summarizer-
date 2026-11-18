"""Read/unread status of stories, per user."""
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal, init_db
from app.core.models import StoryDB, StoryReadDB


class StoryNotFoundError(Exception):
    pass


def list_read_ids(user_id: int) -> list[int]:
    init_db()
    with SessionLocal() as session:
        rows = session.query(StoryReadDB.story_id).filter(StoryReadDB.user_id == user_id).all()
        return sorted(r[0] for r in rows)


def mark_read(user_id: int, story_id: int) -> bool:
    """True if newly marked, False if it was already read."""
    init_db()
    with SessionLocal() as session:
        if session.get(StoryDB, story_id) is None:
            raise StoryNotFoundError("Story nahi mili")
        exists = (
            session.query(StoryReadDB)
            .filter(StoryReadDB.user_id == user_id, StoryReadDB.story_id == story_id)
            .first()
        )
        if exists:
            return False
        session.add(StoryReadDB(user_id=user_id, story_id=story_id))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return False
        return True


def mark_unread(user_id: int, story_id: int) -> bool:
    init_db()
    with SessionLocal() as session:
        row = (
            session.query(StoryReadDB)
            .filter(StoryReadDB.user_id == user_id, StoryReadDB.story_id == story_id)
            .first()
        )
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True
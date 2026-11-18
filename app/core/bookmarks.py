"""Per-user bookmarked stories."""
from app.core.database import SessionLocal, init_db
from app.core.models import BookmarkDB, StoryDB
from app.core.storage import _story_to_dict

MAX_PER_USER = 200


class StoryNotFoundError(Exception):
    """Story id is not in the database."""


class BookmarkLimitError(Exception):
    """User reached the bookmark limit."""


def add_bookmark(user_id: int, story_id: int) -> bool:
    """True if newly saved, False if it was already saved."""
    init_db()
    with SessionLocal() as session:
        if session.get(StoryDB, story_id) is None:
            raise StoryNotFoundError("Story nahi mili")
        mine = session.query(BookmarkDB).filter(BookmarkDB.user_id == user_id)
        if mine.filter(BookmarkDB.story_id == story_id).first():
            return False
        if mine.count() >= MAX_PER_USER:
            raise BookmarkLimitError(f"Sirf {MAX_PER_USER} stories save ho sakti hain")
        session.add(BookmarkDB(user_id=user_id, story_id=story_id))
        session.commit()
        return True


def remove_bookmark(user_id: int, story_id: int) -> bool:
    init_db()
    with SessionLocal() as session:
        row = (
            session.query(BookmarkDB)
            .filter(BookmarkDB.user_id == user_id, BookmarkDB.story_id == story_id)
            .first()
        )
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def list_bookmarked_stories(user_id: int) -> list[dict]:
    """Saved stories, most recently saved first."""
    init_db()
    with SessionLocal() as session:
        rows = (
            session.query(StoryDB)
            .join(BookmarkDB, BookmarkDB.story_id == StoryDB.id)
            .filter(BookmarkDB.user_id == user_id)
            .order_by(BookmarkDB.created_at.desc(), BookmarkDB.id.desc())
            .all()
        )
        return [_story_to_dict(r) for r in rows]
"""Remove duplicate stories (same first source link) left by repeated digests.

Dry run by default:   python -m scripts.dedupe_stories
Delete duplicates:    python -m scripts.dedupe_stories --apply
The oldest copy of each story is kept.
"""
import json
import sys

from app.core.database import SessionLocal, init_db
from app.core.models import BookmarkDB, StoryDB, StoryReadDB


def story_key(row) -> str:
    try:
        sources = json.loads(row.sources_json or "[]")
    except ValueError:
        sources = []
    if sources and len(sources[0]) == 2 and sources[0][1]:
        return sources[0][1]
    return row.title


def find_duplicates(session) -> list:
    seen: dict[str, int] = {}
    dupes = []
    for row in session.query(StoryDB).order_by(StoryDB.id).all():
        key = story_key(row)
        if key in seen:
            dupes.append(row)
        else:
            seen[key] = row.id
    return dupes


def main(argv=None) -> int:
    apply = "--apply" in (argv if argv is not None else sys.argv)
    init_db()
    with SessionLocal() as session:
        dupes = find_duplicates(session)
        for row in dupes:
            print(f"duplicate id={row.id}: {row.title[:80]}")
        if not dupes:
            print("No duplicate stories found.")
            return 0
        if not apply:
            print(f"{len(dupes)} duplicates found. Run with --apply to delete them.")
            return 0
        ids = [r.id for r in dupes]
        session.query(BookmarkDB).filter(BookmarkDB.story_id.in_(ids)).delete(synchronize_session=False)
        session.query(StoryReadDB).filter(StoryReadDB.story_id.in_(ids)).delete(synchronize_session=False)
        session.query(StoryDB).filter(StoryDB.id.in_(ids)).delete(synchronize_session=False)
        session.commit()
        print(f"Deleted {len(ids)} duplicate stories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
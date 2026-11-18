"""Count (and with --yes delete) the seeded demo stories whose title starts with 'Demo:'."""
import sys

from sqlalchemy import text

from app.core.database import engine


def main() -> None:
    with engine.begin() as conn:
        n = conn.execute(text("select count(*) from stories where title like 'Demo:%'")).scalar()
        print(f"Demo stories found: {n}")
        if "--yes" in sys.argv and n:
            done = conn.execute(text("delete from stories where title like 'Demo:%'")).rowcount
            print(f"Deleted: {done}")
        elif n:
            print("Nothing deleted. Run again with --yes to delete them.")


if __name__ == "__main__":
    main()
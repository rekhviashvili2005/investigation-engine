from pathlib import Path

import psycopg

from app.core.config import settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "app" / "db" / "schema.sql"


def main() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(sql)
        conn.commit()
    print("Schema created.")


if __name__ == "__main__":
    main()
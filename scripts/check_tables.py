import psycopg

from app.core.config import settings

with psycopg.connect(settings.database_url) as conn:
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    ).fetchall()
    print("Tables:", [t[0] for t in tables])

    ext = conn.execute(
        "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
    ).fetchone()
    print("pgvector:", ext)
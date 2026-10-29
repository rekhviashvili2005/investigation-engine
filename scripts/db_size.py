from app.db.connection import get_connection

with get_connection() as conn:
    print("DB size:", conn.execute("SELECT pg_size_pretty(pg_database_size(current_database()))").fetchone()[0])
    for t in ("documents", "chunks", "chunks_fixed", "eval_questions"):
        print(t, conn.execute("SELECT pg_size_pretty(pg_tni README.mdotal_relation_size(%s))", (t,)).fetchone()[0])
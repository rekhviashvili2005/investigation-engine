import psycopg

from app.ingestion.embedder import embed_query
from app.retrieval.models import Hit


def dense_search(conn: psycopg.Connection, query: str, k: int = 20) -> list[Hit]:
    vec = str(embed_query(query))
    rows = conn.execute(
        """SELECT c.id, c.document_id, d.title, d.source, c.content,
                  1 - (c.embedding <=> %s::vector) AS similarity
           FROM chunks c JOIN documents d ON d.id = c.document_id
           ORDER BY c.embedding <=> %s::vector
           LIMIT %s""",
        (vec, vec, k),
    ).fetchall()
    return [
        Hit(chunk_id=r[0], document_id=r[1], title=r[2], source=r[3], content=r[4], score=float(r[5]))
        for r in rows
    ]
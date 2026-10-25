import json

import psycopg

from app.ingestion.models import Chunk, ParsedDocument
from app.ingestion.dedup import content_hash


def find_by_hash(conn: psycopg.Connection, hash_: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM documents WHERE content_hash = %s", (hash_,)
    ).fetchone()
    return row[0] if row else None


def find_by_source(conn: psycopg.Connection, source: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM documents WHERE source = %s", (source,)
    ).fetchone()
    return row[0] if row else None


def insert_document(conn: psycopg.Connection, doc: ParsedDocument) -> int:
    row = conn.execute(
        """INSERT INTO documents (title, source, format, content_hash, metadata)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (doc.title, doc.source, doc.format, content_hash(doc.text),
         json.dumps(doc.metadata, default=str)),
    ).fetchone()
    return row[0]


def insert_chunks(
    conn: psycopg.Connection,
    document_id: int,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO chunks (document_id, chunk_index, content, embedding)
               VALUES (%s, %s, %s, %s::vector)""",
            [(document_id, c.index, c.text, str(e)) for c, e in zip(chunks, embeddings)],
        )


def delete_document(conn: psycopg.Connection, document_id: int) -> bool:
    cur = conn.execute("DELETE FROM documents WHERE id = %s", (document_id,))
    return cur.rowcount > 0


def update_document(conn: psycopg.Connection, document_id: int, doc: ParsedDocument) -> None:
    """განახლება: მეტამონაცემებს ვცვლით, ძველ chunk-ებს ვშლით (ახლებს pipeline ჩაწერს)."""
    conn.execute(
        """UPDATE documents SET title=%s, format=%s, content_hash=%s,
           metadata=%s, updated_at=now() WHERE id=%s""",
        (doc.title, doc.format, content_hash(doc.text),
         json.dumps(doc.metadata, default=str), document_id),
    )
    conn.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))


def list_documents(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT d.id, d.title, d.source, d.format, d.created_at,
                  (SELECT count(*) FROM chunks c WHERE c.document_id = d.id)
           FROM documents d ORDER BY d.id DESC"""
    ).fetchall()
    return [
        {"id": r[0], "title": r[1], "source": r[2], "format": r[3],
         "created_at": r[4], "chunks": r[5]}
        for r in rows
    ]
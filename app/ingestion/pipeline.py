from dataclasses import dataclass

import psycopg

from app.db import repository as repo
from app.ingestion.chunking import chunk_text
from app.ingestion.dedup import content_hash
from app.ingestion.embedder import embed_texts
from app.ingestion.models import ParsedDocument


@dataclass
class IngestResult:
    status: str            # "inserted" | "updated" | "duplicate"
    document_id: int | None
    chunks: int = 0


def ingest_document(
    conn: psycopg.Connection,
    doc: ParsedDocument,
    strategy: str = "sentence",
    embed=embed_texts,         # ტესტებში ჩანაცვლება შეიძლება
) -> IngestResult:
    new_hash = content_hash(doc.text)

    # 1) ზუსტი დუბლიკატი (იგივე შინაარსი უკვე არის)
    existing = repo.find_by_hash(conn, new_hash)
    if existing is not None:
        return IngestResult("duplicate", existing)

    chunks = chunk_text(doc.text, strategy=strategy)
    if not chunks:
        return IngestResult("duplicate", None)   # ცარიელი ტექსტი
    embeddings = embed([c.text for c in chunks])

    # 2) იგივე source, ახალი შინაარსი = განახლება
    same_source = repo.find_by_source(conn, doc.source)
    if same_source is not None:
        repo.update_document(conn, same_source, doc)
        repo.insert_chunks(conn, same_source, chunks, embeddings)
        conn.commit()
        return IngestResult("updated", same_source, len(chunks))

    # 3) ახალი დოკუმენტი
    doc_id = repo.insert_document(conn, doc)
    repo.insert_chunks(conn, doc_id, chunks, embeddings)
    conn.commit()
    return IngestResult("inserted", doc_id, len(chunks))
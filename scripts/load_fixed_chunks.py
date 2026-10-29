import re
from pathlib import Path

from app.db.connection import get_connection
from app.ingestion.chunking import fixed_chunks
from app.ingestion.embedder import embed_texts
from app.ingestion.parsers import parse_file

SRC_RE = re.compile(r"<!-- source: (\S+) -->")


def main() -> None:
    files = sorted(Path("data/postmortems").glob("*.html"))
    print(f"Files: {len(files)}")
    done = 0
    for f in files:
        m = SRC_RE.search(f.read_text(encoding="utf-8", errors="replace")[:300])
        if not m:
            continue
        source = f"postmortem://{m.group(1)}"
        doc = parse_file(f)[0]
        chunks = fixed_chunks(doc.text, size=800, overlap=100)
        if not chunks:
            continue
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM documents WHERE source = %s", (source,)).fetchone()
            if row is None:
                continue
            doc_id = row[0]
            exists = conn.execute(
                "SELECT 1 FROM chunks_fixed WHERE document_id = %s LIMIT 1", (doc_id,)
            ).fetchone()
            if exists:
                continue
        embeddings = embed_texts([c.text for c in chunks])
        with get_connection() as conn:
            for c, e in zip(chunks, embeddings):
                conn.execute(
                    "INSERT INTO chunks_fixed (document_id, chunk_index, content, embedding) "
                    "VALUES (%s, %s, %s, %s::vector) ON CONFLICT DO NOTHING",
                    (doc_id, c.index, c.text, str(e)),
                )
            conn.commit()
        done += 1
        print(f"  {done}: {len(chunks)} chunks  {doc.title[:50]}")
    print("Done.")


if __name__ == "__main__":
    main()
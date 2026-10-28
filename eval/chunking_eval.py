"""fixed vs sentence chunking: document-level Recall@K (dense ძიება).

გაშვება: python -m eval.chunking_eval --k 5
"""
import argparse
import json
from pathlib import Path
from statistics import mean

from app.db.connection import get_connection
from app.ingestion.embedder import embed_query

TABLES = {"sentence": "chunks", "fixed": "chunks_fixed"}


def top_docs(conn, table: str, vec: str, k: int) -> list[int]:
    rows = conn.execute(
        f"SELECT document_id FROM {table} ORDER BY embedding <=> %s::vector LIMIT %s",
        (vec, k),
    ).fetchall()
    return [r[0] for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    qs = [q for q in json.loads(Path("eval/postmortem_questions.json").read_text(encoding="utf-8"))
          if q["supporting_doc_ids"]]
    print(f"Questions: {len(qs)}, K={args.k}")

    with get_connection() as conn:
        n_chunks = {name: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                    for name, t in TABLES.items()}
        print("chunks:", n_chunks)
        report = {}
        for name, table in TABLES.items():
            recalls, hits = [], []
            for q in qs:
                docs = top_docs(conn, table, str(embed_query(q["question"])), args.k)
                rel = set(q["supporting_doc_ids"])
                recalls.append(len(rel & set(docs)) / len(rel))
                hits.append(1.0 if rel & set(docs) else 0.0)
            report[name] = {"doc_recall": round(mean(recalls), 3),
                            "any_hit": round(mean(hits), 3), "chunks": n_chunks[name]}
            print(f"{name:9} doc_recall@{args.k}={report[name]['doc_recall']}  "
                  f"any_hit={report[name]['any_hit']}  chunks={n_chunks[name]}")

    Path("eval/chunking_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
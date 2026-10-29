
import argparse
import re

from app.db.connection import get_connection


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phrase")
    ap.add_argument("--max", type=int, default=8, help="მაქს. დოკუმენტი")
    ap.add_argument("--width", type=int, default=150, help="ამონარიდის ნახევარსიგრძე")
    args = ap.parse_args()

    with get_connection() as conn:
        rows = conn.execute(
            """SELECT d.id, d.title, d.source, c.content
               FROM chunks c JOIN documents d ON d.id = c.document_id
               WHERE d.source LIKE 'postmortem://%%' AND c.content ILIKE %s
               ORDER BY d.id, c.chunk_index""",
            (f"%{args.phrase}%",),
        ).fetchall()

    pattern = re.compile(re.escape(args.phrase), re.IGNORECASE)
    seen_docs: dict[int, int] = {}
    shown_docs = 0
    for doc_id, title, source, content in rows:
        if doc_id not in seen_docs:
            if shown_docs >= args.max:
                break
            shown_docs += 1
            seen_docs[doc_id] = 0
            print(f"\n=== [{doc_id}] {title}\n    {source}")
        if seen_docs[doc_id] >= 2:
            continue
        seen_docs[doc_id] += 1
        m = pattern.search(content)
        start = max(0, m.start() - args.width)
        end = min(len(content), m.end() + args.width)
        print(f"  ...{content[start:end].replace(chr(10), ' ')}...")

    print(f"\nMatching chunks: {len(rows)}, documents shown: {shown_docs}")


if __name__ == "__main__":
    main()
"""data/postmortems/*.html -> ბაზა (parse -> chunk -> dedup -> embed -> insert).

გაშვება: python -m scripts.load_postmortems --strategy sentence
"""
import argparse
import re
from pathlib import Path

from app.db.connection import get_connection
from app.ingestion.parsers import parse_file
from app.ingestion.pipeline import ingest_document

SRC_RE = re.compile(r"<!-- source: (\S+) -->")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="sentence", choices=["sentence", "fixed"])
    ap.add_argument("--dir", default="data/postmortems")
    args = ap.parse_args()

    files = sorted(Path(args.dir).glob("*.html"))
    print(f"Files: {len(files)}, strategy: {args.strategy}")
    stats = {"inserted": 0, "updated": 0, "duplicate": 0, "failed": 0}

    for f in files:
        try:
            doc = parse_file(f)[0]
            m = SRC_RE.search(f.read_text(encoding="utf-8", errors="replace")[:300])
            if m:
                doc.source = f"postmortem://{m.group(1)}"   # რეალური URL წყაროდ
            if len(doc.text) < 500:                          # ძალიან მოკლე/ცარიელი გვერდი
                stats["failed"] += 1
                continue
            with get_connection() as conn:                   # მოკლე კავშირი თითო დოკუმენტზე
                res = ingest_document(conn, doc, strategy=args.strategy)
            stats[res.status] += 1
            print(f"  {res.status:9} {res.chunks:3} chunks  {doc.title[:55]}")
        except Exception as e:
            stats["failed"] += 1
            print(f"  FAILED {f.name}: {type(e).__name__}: {e}")
    print(stats)


if __name__ == "__main__":
    main()
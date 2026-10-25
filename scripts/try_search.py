import sys

from app.db.connection import get_connection
from app.retrieval.search import hybrid_search

query = " ".join(sys.argv[1:]) or "Which magazine was started first?"
with get_connection() as conn:
    for mode in ("dense", "bm25", "hybrid"):
        print(f"\n=== {mode} ===")
        for h in hybrid_search(conn, query, k=5, mode=mode):
            print(f"{h.score:.3f}  {h.title}: {h.content[:90]}...")
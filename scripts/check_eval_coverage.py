import json

from app.db.connection import get_connection

with get_connection() as conn:
    titles = {r[0] for r in conn.execute("SELECT title FROM documents").fetchall()}
    rows = conn.execute("SELECT id, supporting FROM eval_questions").fetchall()

missing_q = 0
missing_t = 0
for _id, sup in rows:
    miss = [t for t in sup if t not in titles]
    if miss:
        missing_q += 1
        missing_t += len(miss)
print(f"questions: {len(rows)}, with missing supporting: {missing_q}, missing titles: {missing_t}")
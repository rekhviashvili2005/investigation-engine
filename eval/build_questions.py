import json
import random

from app.db.connection import get_connection

SEED = 42
PER_TYPE = 10


def main() -> None:
    with get_connection() as conn:
        titles = {r[0] for r in conn.execute("SELECT title FROM documents").fetchall()}
        rows = conn.execute(
            "SELECT id, question, answer, qtype, supporting FROM eval_questions ORDER BY id"
        ).fetchall()

    covered = [r for r in rows if set(r[4]) <= titles]
    rng = random.Random(SEED)
    comparison = [r for r in covered if r[3] == "comparison"]
    bridge = [r for r in covered if r[3] == "bridge"]
    rng.shuffle(comparison)
    rng.shuffle(bridge)

    out = []
    for r in comparison[:PER_TYPE]:
        out.append({"id": r[0], "category": "simple", "question": r[1],
                    "expected": r[2], "supporting": r[4]})
    for r in bridge[:PER_TYPE]:
        out.append({"id": r[0], "category": "multi_hop", "question": r[1],
                    "expected": r[2], "supporting": r[4]})
    for r in bridge[PER_TYPE:2 * PER_TYPE]:
        out.append({"id": r[0], "category": "unanswerable", "question": r[1],
                    "expected": None, "supporting": r[4]})   # supporting გამოირიცხება ძიებიდან

    with open("eval/questions.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    counts = {c: sum(1 for q in out if q["category"] == c) for c in ("simple", "multi_hop", "unanswerable")}
    print(counts, "-> eval/questions.json")


if __name__ == "__main__":
    main()
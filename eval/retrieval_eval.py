import argparse
import json
from statistics import mean

from app.db.connection import get_connection
from app.retrieval.search import hybrid_search
from eval.metrics import full_hit_at_k, recall_at_k, reciprocal_rank


CONFIGS = {
    "dense":              {"mode": "dense",  "rerank": False},
    "bm25":               {"mode": "bm25",   "rerank": False},
    "hybrid 1:1":         {"mode": "hybrid", "rerank": False},
    "hybrid 2:1":         {"mode": "hybrid", "rerank": False, "dense_weight": 2.0, "bm25_weight": 1.0},
    "hybrid 3:1":         {"mode": "hybrid", "rerank": False, "dense_weight": 3.0, "bm25_weight": 1.0},
    "hybrid 3:1+rerank":  {"mode": "hybrid", "rerank": True,  "dense_weight": 3.0, "bm25_weight": 1.0},
}

def load_questions(conn, n: int) -> list[dict]:
    titles = {r[0] for r in conn.execute("SELECT title FROM documents").fetchall()}
    rows = conn.execute(
        "SELECT id, question, qtype, supporting FROM eval_questions ORDER BY id"
    ).fetchall()
    out = []
    for r in rows:
        relevant = set(r[3])
        if relevant <= titles:            # ყველა supporting ბაზაშია
            out.append({"id": r[0], "question": r[1], "qtype": r[2], "relevant": relevant})
    return out[:n]


def evaluate(conn, questions: list[dict], k: int) -> dict:
    report = {}
    for name, cfg in CONFIGS.items():
        rec, rr, full = [], [], []
        by_type: dict[str, list[float]] = {}
        failures = []
        for q in questions:
            hits = hybrid_search(conn, q["question"], k=k, **cfg)
            titles = [h.title for h in hits]
            r = recall_at_k(titles, q["relevant"], k)
            rec.append(r)
            rr.append(reciprocal_rank(titles, q["relevant"]))
            full.append(full_hit_at_k(titles, q["relevant"], k))
            by_type.setdefault(q["qtype"], []).append(r)
            if r < 1.0:
                failures.append({"id": q["id"], "question": q["question"],
                                 "missing": sorted(q["relevant"] - set(titles))})
        report[name] = {
            f"recall@{k}": round(mean(rec), 3),
            "mrr": round(mean(rr), 3),
            f"full_hit@{k}": round(mean(full), 3),
            "by_type_recall": {t: round(mean(v), 3) for t, v in by_type.items()},
            "failures": failures[:10],      # ანალიზისთვის პირველი 10
        }
        print(f"{name:15} recall@{k}={report[name][f'recall@{k}']}  "
              f"mrr={report[name]['mrr']}  full_hit={report[name][f'full_hit@{k}']}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()

    with get_connection() as conn:
        questions = load_questions(conn, args.n)
        print(f"Questions: {len(questions)}, K={args.k}")
        report = evaluate(conn, questions, args.k)

    with open("eval/retrieval_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Saved eval/retrieval_results.json")


if __name__ == "__main__":
    main()
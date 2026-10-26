"""პასუხების შეფასება კონფიგურაციების მიხედვით.

გაშვება: python -m eval.answer_eval --limit 30
შედეგები ინახება ყოველი კითხვის შემდეგ: eval/answer_results.json
"""
import argparse
import json
import time
from pathlib import Path
from statistics import mean

from app.db.connection import get_connection
from app.llm.agent import run_agent
from app.llm.client import LLMClient
from eval.answer_metrics import answer_correct, citation_accuracy

QUESTIONS = Path("eval/questions.json")
RESULTS = Path("eval/answer_results.json")
PAUSE_S = 4          # პაუზა კითხვებს შორის (ლიმიტების გამო)

CONFIGS = {
    "dense":      {"mode": "dense",  "rerank": False},
    "hybrid 3:1": {"mode": "hybrid", "rerank": False},   # წონები search.py-ში ნაგულისხმევია 1:1; იხ. ქვემოთ
}


def run_one(conn, llm, q: dict, cfg: dict) -> dict:
    exclude = frozenset(q["supporting"]) if q["category"] == "unanswerable" else None
    a = run_agent(conn, q["question"], llm=llm, exclude_titles=exclude, **cfg)
    cited_titles = [s["title"] for s in a.sources]
    row = {
        "id": q["id"], "category": q["category"], "status": a.status,
        "answer": a.answer, "expected": q["expected"],
        "cited": cited_titles, "missing": a.missing,
    }
    if q["category"] == "unanswerable":
        row["abstained"] = a.status in ("insufficient_evidence", "error")
    else:
        row["correct"] = a.status == "answered" and answer_correct(a.answer, q["expected"])
        row["citation_acc"] = citation_accuracy(cited_titles, q["supporting"])
    return row


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["category"] != "unanswerable"]
    una = [r for r in rows if r["category"] == "unanswerable"]
    out = {}
    for cat in ("simple", "multi_hop"):
        sub = [r for r in ans if r["category"] == cat]
        if sub:
            out[f"correctness_{cat}"] = round(mean(r["correct"] for r in sub), 3)
    if ans:
        out["citation_accuracy"] = round(mean(r["citation_acc"] for r in ans), 3)
    if una:
        out["abstention_accuracy"] = round(mean(r["abstained"] for r in una), 3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))[: args.limit]
    saved = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {}
    llm = LLMClient()

    for name, cfg in CONFIGS.items():
        rows = saved.setdefault(name, [])
        done = {r["id"] for r in rows}
        for q in questions:
            if q["id"] in done:
                continue
            with get_connection() as conn:
                row = run_one(conn, llm, q, cfg)
            rows.append(row)
            RESULTS.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{name}] {q['category']:12} status={row['status']:22} "
                  f"{'OK' if row.get('correct') or row.get('abstained') else '--'}")
            time.sleep(PAUSE_S)
        print(f"== {name}: {summarize(rows)}")


if __name__ == "__main__":
    main()
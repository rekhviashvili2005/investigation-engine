"""ჩატვირთავს სინთეზურ დოკუმენტებს (ერთხელ) და ამოწმებს conflict-ის აღმოჩენას.

გაშვება: python -m eval.conflict_eval
"""
import time

from app.db.connection import get_connection
from app.ingestion.models import ParsedDocument
from app.ingestion.pipeline import ingest_document
from app.llm.agent import run_agent
from eval.conflict_docs import DOCS, QUESTIONS


def load_docs() -> None:
    with get_connection() as conn:
        for title, source, text in DOCS:
            doc = ParsedDocument(title=title, source=source, format="txt", text=text)
            res = ingest_document(conn, doc, strategy="sentence")
            print(f"  {res.status:9} {title[:60]}")


def main() -> None:
    print("Loading synthetic documents...")
    load_docs()

    ok = 0
    for question, expected, keyword in QUESTIONS:
        with get_connection() as conn:
            a = run_agent(conn, question, mode="hybrid", rerank=False)
        passed = a.status == expected
        if passed and keyword:
            passed = keyword in a.answer.lower()
        ok += passed
        print(f"\nQ: {question}\n  expected={expected} got={a.status} -> {'PASS' if passed else 'FAIL'}")
        print(f"  answer: {a.answer[:200]}")
        if a.conflicts:
            print(f"  conflicts: {a.conflicts}")
        time.sleep(4)
    print(f"\nConflict eval: {ok}/{len(QUESTIONS)} passed")


if __name__ == "__main__":
    main()
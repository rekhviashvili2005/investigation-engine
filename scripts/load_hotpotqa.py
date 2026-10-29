# """HotpotQA (distractor, validation) -> documents/chunks + eval_questions.
#
# გაშვება:  python -m scripts.load_hotpotqa --questions 150
#
# სკრიპტი გაგრძელებადია: ბაზაში უკვე არსებული პარაგრაფები გამოტოვებულია
# embedding-ის გამოთვლამდე, ამიტომ ნებისმიერ დროს შეგიძლია გააჩერო (Ctrl+C)
# და ხელახლა გაუშვა.
# """
# import argparse
# import json
#
# from datasets import load_dataset
#
# from app.db.connection import get_connection
# from app.ingestion.dedup import content_hash
# from app.ingestion.embedder import embed_texts
#
# BATCH = 128
#
#
# def collect_paragraphs(rows) -> dict[str, tuple[str, str]]:
#     """title -> (text, hash). ერთი და იგივე სათაური ბევრ კითხვაში მეორდება,
#     ამიტომ dict-ით ვშლით დუბლიკატებს."""
#     paras: dict[str, tuple[str, str]] = {}
#     for row in rows:
#         titles = row["context"]["title"]
#         sentences = row["context"]["sentences"]
#         for title, sents in zip(titles, sentences):
#             if title in paras:
#                 continue
#             text = " ".join(s.strip() for s in sents).strip()
#             if text:
#                 paras[title] = (text, content_hash(text))
#     return paras
#
#
# def existing_sources() -> set[str]:
#     """ბაზაში უკვე ჩაწერილი HotpotQA პარაგრაფების source-ები."""
#     with get_connection() as conn:
#         rows = conn.execute(
#             "SELECT source FROM documents WHERE source LIKE 'hotpotqa://%'"
#         ).fetchall()
#     return {r[0] for r in rows}
#
#
# def insert_batch(batch: list[tuple[str, str, str]]) -> None:
#     """batch: [(title, text, hash)]. embeddings ჯერ ბაზის გარეშე ითვლება,
#     შემდეგ ახალი, მოკლე კავშირით ვწერთ (Neon გრძელ უმოქმედო კავშირს წყვეტს)."""
#     embeddings = embed_texts([t for _, t, _ in batch])
#
#     with get_connection() as conn:
#         for (title, text, h), emb in zip(batch, embeddings):
#             row = conn.execute(
#                 """INSERT INTO documents (title, source, format, content_hash, metadata)
#                    VALUES (%s, %s, 'json', %s, %s)
#                    ON CONFLICT DO NOTHING RETURNING id""",
#                 (title, f"hotpotqa://{title}", h, json.dumps({"dataset": "hotpotqa"})),
#             ).fetchone()
#             if row is None:          # დუბლიკატი (source ან hash უკვე არის)
#                 continue
#             conn.execute(
#                 """INSERT INTO chunks (document_id, chunk_index, content, embedding)
#                    VALUES (%s, 0, %s, %s::vector)""",
#                 (row[0], text, str(emb)),
#             )
#         conn.commit()
#
#
# def insert_questions(rows) -> None:
#     with get_connection() as conn:
#         for row in rows:
#             conn.execute(
#                 """INSERT INTO eval_questions (id, question, answer, qtype, supporting)
#                    VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
#                 (row["id"], row["question"], row["answer"], row["type"],
#                  json.dumps(sorted(set(row["supporting_facts"]["title"])))),
#             )
#         conn.commit()
#
#
# def main() -> None:
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--questions", type=int, default=150)
#     args = ap.parse_args()
#
#     ds = load_dataset("hotpotqa/hotpot_qa", "distractor", split="validation")
#     rows = ds.select(range(min(args.questions, len(ds))))   # დეტერმინირებული subset
#
#     paras = collect_paragraphs(rows)
#     print(f"Questions: {len(rows)}, unique paragraphs: {len(paras)}")
#
#     insert_questions(rows)
#
#     done = existing_sources()
#     items = [
#         (t, text, h) for t, (text, h) in paras.items()
#         if f"hotpotqa://{t}" not in done
#     ]
#     print(f"Already in DB: {len(done)}, remaining: {len(items)}")
#
#     for i in range(0, len(items), BATCH):
#         insert_batch(items[i:i + BATCH])
#         print(f"  inserted {min(i + BATCH, len(items))}/{len(items)}")
#     print("Done.")
#
#
# if __name__ == "__main__":
#     main()



"""HotpotQA (distractor, validation) -> documents/chunks + eval_questions.

გაშვება:  python -m scripts.load_hotpotqa --questions 5500

გაგრძელებადია: ბაზაში არსებული პარაგრაფები embedding-მდე გამოტოვებულია.
"""
import argparse
import json
import time

from datasets import load_dataset

from app.db.connection import get_connection
from app.ingestion.dedup import content_hash
from app.ingestion.embedder import _model

BATCH = 512


def collect_paragraphs(rows) -> dict[str, tuple[str, str]]:
    paras: dict[str, tuple[str, str]] = {}
    for row in rows:
        for title, sents in zip(row["context"]["title"], row["context"]["sentences"]):
            if title in paras:
                continue
            text = " ".join(s.strip() for s in sents).strip()
            if text:
                paras[title] = (text, content_hash(text))
    return paras


def existing_sources() -> set[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT source FROM documents WHERE source LIKE 'hotpotqa://%'"
        ).fetchall()
    return {r[0] for r in rows}


def embed_batch(texts: list[str]) -> list[list[float]]:
    """fastembed-ის პარალელური რეჟიმი (რამდენიმე პროცესი) და დიდი შიდა ბატჩი."""
    return [v.tolist() for v in _model().embed(texts, batch_size=64, parallel=0)]


def insert_batch(batch: list[tuple[str, str, str]]) -> int:
    embeddings = embed_batch([t for _, t, _ in batch])   # ბაზის კავშირის გარეშე

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO documents (title, source, format, content_hash, metadata)
                   VALUES (%s, %s, 'json', %s, %s) ON CONFLICT DO NOTHING""",
                [(t, f"hotpotqa://{t}", h, json.dumps({"dataset": "hotpotqa"}))
                 for t, _, h in batch],
            )
        sources = [f"hotpotqa://{t}" for t, _, _ in batch]
        ids = dict(conn.execute(
            "SELECT source, id FROM documents WHERE source = ANY(%s)", (sources,)
        ).fetchall())
        # chunk მხოლოდ იმას, რასაც ჯერ არ აქვს
        has = {r[0] for r in conn.execute(
            "SELECT document_id FROM chunks WHERE document_id = ANY(%s)", (list(ids.values()),)
        ).fetchall()}
        rows = [
            (ids[f"hotpotqa://{t}"], text, str(emb))
            for (t, text, _), emb in zip(batch, embeddings)
            if f"hotpotqa://{t}" in ids and ids[f"hotpotqa://{t}"] not in has
        ]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, chunk_index, content, embedding) "
                "VALUES (%s, 0, %s, %s::vector)",
                rows,
            )
        conn.commit()
    return len(rows)


def insert_questions(rows) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO eval_questions (id, question, answer, qtype, supporting)
                   VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                [(r["id"], r["question"], r["answer"], r["type"],
                  json.dumps(sorted(set(r["supporting_facts"]["title"])))) for r in rows],
            )
        conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", type=int, default=150)
    args = ap.parse_args()

    ds = load_dataset("hotpotqa/hotpot_qa", "distractor", split="validation")
    rows = ds.select(range(min(args.questions, len(ds))))

    paras = collect_paragraphs(rows)
    print(f"Questions: {len(rows)}, unique paragraphs: {len(paras)}", flush=True)
    insert_questions(rows)

    done = existing_sources()
    items = [(t, x, h) for t, (x, h) in paras.items() if f"hotpotqa://{t}" not in done]
    print(f"Already in DB: {len(done)}, remaining: {len(items)}", flush=True)

    start = time.time()
    for i in range(0, len(items), BATCH):
        insert_batch(items[i:i + BATCH])
        n = min(i + BATCH, len(items))
        rate = n / (time.time() - start) * 60
        print(f"  inserted {n}/{len(items)}  (~{rate:.0f}/min)", flush=True)
    print("Done.")


if __name__ == "__main__":
    main()
# # import psycopg
# #
# # from app.retrieval.bm25 import bm25_search
# # from app.retrieval.dense import dense_search
# # from app.retrieval.fusion import rrf_fuse
# # from app.retrieval.models import Hit
# # from app.retrieval.rerank import mmr_rerank
# #
# #
# # def hybrid_search(
# #     conn: psycopg.Connection,
# #     query: str,
# #     k: int = 8,
# #     mode: str = "hybrid",     # "dense" | "bm25" | "hybrid"
# #     rerank: bool = True,
# #     pool: int = 30,
# # ) -> list[Hit]:
# #     if mode == "dense":
# #         hits = dense_search(conn, query, pool)
# #     elif mode == "bm25":
# #         hits = bm25_search(conn, query, pool)
# #     elif mode == "hybrid":
# #         hits = rrf_fuse(
# #             [dense_search(conn, query, pool), bm25_search(conn, query, pool)],
# #             top_n=pool,
# #         )
# #     else:
# #         raise ValueError(f"Unknown mode: {mode}")
# #
# #     return mmr_rerank(hits, k=k) if rerank else hits[:k]
#
#
# import psycopg
#
# from app.retrieval.bm25 import bm25_search
# from app.retrieval.dense import dense_search
# from app.retrieval.fusion import rrf_fuse
# from app.retrieval.models import Hit
# from app.retrieval.rerank import mmr_rerank
#
#
# def hybrid_search(
#     conn: psycopg.Connection,
#     query: str,
#     k: int = 8,
#     mode: str = "hybrid",     # "dense" | "bm25" | "hybrid"
#     rerank: bool = True,
#     pool: int = 30,
#     dense_weight: float = 1.0,
#     bm25_weight: float = 1.0,
# ) -> list[Hit]:
#     if mode == "dense":
#         hits = dense_search(conn, query, pool)
#     elif mode == "bm25":
#         hits = bm25_search(conn, query, pool)
#     elif mode == "hybrid":
#         hits = rrf_fuse(
#             [dense_search(conn, query, pool), bm25_search(conn, query, pool)],
#             top_n=pool,
#             weights=[dense_weight, bm25_weight],
#         )
#     else:
#         raise ValueError(f"Unknown mode: {mode}")
#
#     return mmr_rerank(hits, k=k) if rerank else hits[:k]




import psycopg

from app.retrieval.bm25 import bm25_search
from app.retrieval.dense import dense_search
from app.retrieval.fusion import rrf_fuse
from app.retrieval.models import Hit
from app.retrieval.rerank import mmr_rerank


def hybrid_search(
    conn: psycopg.Connection,
    query: str,
    k: int = 8,
    mode: str = "hybrid",     # "dense" | "bm25" | "hybrid"
    rerank: bool = True,
    pool: int = 30,
    dense_weight: float = 3.0, #1.0
    bm25_weight: float = 1.0,
    exclude_titles: frozenset[str] | None = None,
) -> list[Hit]:
    """exclude_titles: ეს სათაურები შედეგიდან ამოიღება (უპასუხო კითხვების ექსპერიმენტისთვის)."""
    extra = pool + (len(exclude_titles) if exclude_titles else 0)
    if mode == "dense":
        hits = dense_search(conn, query, extra)
    elif mode == "bm25":
        hits = bm25_search(conn, query, extra)
    elif mode == "hybrid":
        hits = rrf_fuse(
            [dense_search(conn, query, extra), bm25_search(conn, query, extra)],
            top_n=extra,
            weights=[dense_weight, bm25_weight],
        )
    else:
        raise ValueError(f"Unknown mode: {mode}")

    if exclude_titles:
        hits = [h for h in hits if h.title not in exclude_titles]
    return mmr_rerank(hits, k=k) if rerank else hits[:k]
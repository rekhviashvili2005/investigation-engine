# from app.retrieval.models import Hit
#
#
# def rrf_fuse(result_lists: list[list[Hit]], k: int = 60, top_n: int = 20) -> list[Hit]:
#     fused: dict[int, float] = {}
#     by_id: dict[int, Hit] = {}
#     for hits in result_lists:
#         for rank, hit in enumerate(hits, start=1):
#             fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
#             by_id.setdefault(hit.chunk_id, hit)
#
#     ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
#     out = []
#     for chunk_id, score in ranked:
#         h = by_id[chunk_id]
#         out.append(Hit(h.chunk_id, h.document_id, h.title, h.source, h.content, score))
#     return out


from app.retrieval.models import Hit


def rrf_fuse(
    result_lists: list[list[Hit]],
    k: int = 60,
    top_n: int = 20,
    weights: list[float] | None = None,
) -> list[Hit]:
    """Weighted Reciprocal Rank Fusion.

    score(chunk) = sum_over_lists( w_list / (k + rank) )
    result_lists: თითო სია უკვე დალაგებულია საუკეთესოდან საუკეთესომდე.
    weights: თითო სიის წონა (ნაგულისხმევად ყველა 1.0).
    """
    weights = weights or [1.0] * len(result_lists)
    if len(weights) != len(result_lists):
        raise ValueError("weights must match number of result lists")

    fused: dict[int, float] = {}
    by_id: dict[int, Hit] = {}
    for hits, w in zip(result_lists, weights):
        for rank, hit in enumerate(hits, start=1):
            fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + w / (k + rank)
            by_id.setdefault(hit.chunk_id, hit)

    ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    out = []
    for chunk_id, score in ranked:
        h = by_id[chunk_id]
        out.append(Hit(h.chunk_id, h.document_id, h.title, h.source, h.content, score))
    return out
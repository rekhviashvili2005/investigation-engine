from app.retrieval.models import Hit


def rrf_fuse(result_lists: list[list[Hit]], k: int = 60, top_n: int = 20) -> list[Hit]:
    fused: dict[int, float] = {}
    by_id: dict[int, Hit] = {}
    for hits in result_lists:
        for rank, hit in enumerate(hits, start=1):
            fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            by_id.setdefault(hit.chunk_id, hit)

    ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    out = []
    for chunk_id, score in ranked:
        h = by_id[chunk_id]
        out.append(Hit(h.chunk_id, h.document_id, h.title, h.source, h.content, score))
    return out
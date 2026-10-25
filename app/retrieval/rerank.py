from app.ingestion.dedup import jaccard, shingles
from app.retrieval.models import Hit


def mmr_rerank(hits: list[Hit], k: int = 8, lam: float = 0.7, max_per_doc: int = 1) -> list[Hit]:
    """lam=1 მხოლოდ რელევანტურობა, lam=0 მხოლოდ მრავალფეროვნება.

    მსგავსებას ვზომავთ Jaccard-ით shingle-ებზე (ბაზის გარეშე, სწრაფად).
    max_per_doc: ერთი დოკუმენტიდან მაქსიმუმ რამდენი chunk.
    """
    if not hits:
        return []
    top = max(h.score for h in hits) or 1.0
    norm = {h.chunk_id: h.score / top for h in hits}   # ქულები 0..1-ში
    sh = {h.chunk_id: shingles(h.content, k=3) for h in hits}

    selected: list[Hit] = []
    per_doc: dict[int, int] = {}
    remaining = list(hits)

    while remaining and len(selected) < k:
        best, best_val = None, float("-inf")
        for cand in remaining:
            if per_doc.get(cand.document_id, 0) >= max_per_doc:
                continue
            redundancy = max(
                (jaccard(sh[cand.chunk_id], sh[s.chunk_id]) for s in selected), default=0.0
            )
            val = lam * norm[cand.chunk_id] - (1 - lam) * redundancy
            if val > best_val:
                best, best_val = cand, val
        if best is None:
            break
        selected.append(best)
        per_doc[best.document_id] = per_doc.get(best.document_id, 0) + 1
        remaining.remove(best)
    return selected
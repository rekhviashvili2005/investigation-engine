

def recall_at_k(retrieved_titles: list[str], relevant: set[str], k: int) -> float:

    if not relevant:
        return 0.0
    found = relevant & set(retrieved_titles[:k])
    return len(found) / len(relevant)


def reciprocal_rank(retrieved_titles: list[str], relevant: set[str]) -> float:

    for rank, title in enumerate(retrieved_titles, start=1):
        if title in relevant:
            return 1.0 / rank
    return 0.0


def full_hit_at_k(retrieved_titles: list[str], relevant: set[str], k: int) -> float:

    return 1.0 if relevant and relevant <= set(retrieved_titles[:k]) else 0.0
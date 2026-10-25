"""სუფთა მეტრიკები (ბაზისა და LLM-ის გარეშე), ადვილად ტესტირებადი."""


def recall_at_k(retrieved_titles: list[str], relevant: set[str], k: int) -> float:
    """relevant-იდან რამდენი არის top-k-ში (0..1)."""
    if not relevant:
        return 0.0
    found = relevant & set(retrieved_titles[:k])
    return len(found) / len(relevant)


def reciprocal_rank(retrieved_titles: list[str], relevant: set[str]) -> float:
    """1 / პირველი სწორი შედეგის ადგილი (0, თუ არცერთი არ არის)."""
    for rank, title in enumerate(retrieved_titles, start=1):
        if title in relevant:
            return 1.0 / rank
    return 0.0


def full_hit_at_k(retrieved_titles: list[str], relevant: set[str], k: int) -> float:
    """1, თუ ყველა სწორი პარაგრაფი მოხვდა top-k-ში (multi-hop-ისთვის მნიშვნელოვანია)."""
    return 1.0 if relevant and relevant <= set(retrieved_titles[:k]) else 0.0
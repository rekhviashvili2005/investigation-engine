from functools import lru_cache

from fastembed import TextEmbedding

from app.core.config import settings


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    # მოდელი იტვირთება ერთხელ (პირველ გამოძახებაზე ჩამოიტვირთება ~130MB)
    return TextEmbedding(model_name=settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """ტექსტების სია -> ვექტორების სია (თითო 384 რიცხვი)."""
    if not texts:
        return []
    return [vec.tolist() for vec in _model().embed(texts)]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
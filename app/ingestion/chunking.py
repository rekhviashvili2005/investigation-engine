import re

from app.ingestion.models import Chunk


def fixed_chunks(text: str, size: int = 800, overlap: int = 100) -> list[Chunk]:
    """სტრატეგია A: ფიქსირებული ზომა სიმბოლოებით, overlap-ით."""
    if size <= overlap:
        raise ValueError("size must be greater than overlap")
    text = text.strip()
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(Chunk(len(chunks), text[start:end], start, end))
        if end == len(text):
            break
        start = end - overlap
    return chunks


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def sentence_chunks(text: str, max_chars: int = 800, overlap_sentences: int = 1) -> list[Chunk]:
    """სტრატეგია B: წინადადების საზღვრებს ვინარჩუნებთ."""
    text = text.strip()
    sentences = [s for s in _SENTENCE_RE.split(text) if s]
    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0
    cursor = 0

    def flush() -> None:
        nonlocal cursor
        body = " ".join(current)
        start = text.find(current[0], cursor)
        start = start if start != -1 else cursor
        chunks.append(Chunk(len(chunks), body, start, start + len(body)))
        cursor = start

    for sent in sentences:
        if current and current_len + len(sent) + 1 > max_chars:
            flush()
            current = current[-overlap_sentences:] if overlap_sentences else []
            current_len = sum(len(s) + 1 for s in current)
        current.append(sent)
        current_len += len(sent) + 1
    if current:
        flush()
    return chunks


def chunk_text(text: str, strategy: str = "sentence", **kwargs) -> list[Chunk]:
    if strategy == "fixed":
        return fixed_chunks(text, **kwargs)
    if strategy == "sentence":
        return sentence_chunks(text, **kwargs)
    raise ValueError(f"Unknown chunking strategy: {strategy}")
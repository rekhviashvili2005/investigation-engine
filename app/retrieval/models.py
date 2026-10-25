from dataclasses import dataclass


@dataclass
class Hit:
    chunk_id: int
    document_id: int
    title: str
    source: str
    content: str
    score: float = 0.0
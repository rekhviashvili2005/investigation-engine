from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    mode: str = Field(default="hybrid", pattern="^(dense|bm25|hybrid)$")


class SourceOut(BaseModel):
    id: int
    title: str
    source: str
    text: str


class AskResponse(BaseModel):
    status: str
    answer: str
    citations: list[int]
    conflicts: list[str]
    missing: str
    sources: list[SourceOut]
    trace: list[dict]


class DocumentOut(BaseModel):
    id: int
    title: str
    source: str
    format: str
    chunks: int


class IngestOut(BaseModel):
    status: str
    document_id: int | None
    chunks: int
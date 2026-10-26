"""ინსტრუმენტები LLM-ისთვის. ყველა მტკიცებულებას ეძლევა ნომერი (ციტირებისთვის)."""
from dataclasses import dataclass, field

import psycopg

from app.llm.client import ToolSpec
from app.retrieval.models import Hit
from app.retrieval.search import hybrid_search

SEARCH_TOOL = ToolSpec(
    name="search_documents",
    description=(
        "Search the document collection and return numbered evidence passages. "
        "Use short, specific queries with entity names. Call again with new facts for multi-step questions."
    ),
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "search query"}},
        "required": ["query"],
    },
)


@dataclass
class EvidenceStore:
    """ყველა ნაპოვნი chunk ერთ ნომრიან რეესტრში. ნომერი ციტატის [n] იდენტიფიკატორია."""
    items: dict[int, Hit] = field(default_factory=dict)     # ნომერი -> Hit
    _by_chunk: dict[int, int] = field(default_factory=dict)  # chunk_id -> ნომერი

    def add(self, hit: Hit) -> int:
        if hit.chunk_id in self._by_chunk:
            return self._by_chunk[hit.chunk_id]
        n = len(self.items) + 1
        self.items[n] = hit
        self._by_chunk[hit.chunk_id] = n
        return n


def run_search(conn: psycopg.Connection, store: EvidenceStore, query: str,
               k: int = 5, mode: str = "hybrid", rerank: bool = True,
               exclude_titles: frozenset[str] | None = None) -> dict:
    hits = hybrid_search(conn, query, k=k, mode=mode, rerank=rerank,
                         exclude_titles=exclude_titles)
    results = []
    for h in hits:
        n = store.add(h)
        results.append({"id": n, "title": h.title, "text": h.content})
    return {"results": results}


def execute_tool(conn: psycopg.Connection, store: EvidenceStore, name: str, args: dict,
                 **search_kwargs) -> dict:
    if name == "search_documents":
        query = str(args.get("query", "")).strip()
        if not query:
            return {"error": "empty query"}
        return run_search(conn, store, query, **search_kwargs)
    return {"error": f"unknown tool: {name}"}
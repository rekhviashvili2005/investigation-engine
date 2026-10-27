"""FastAPI: დოკუმენტების მართვა + კითხვა-პასუხი."""
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.api.schemas import AskRequest, AskResponse, DocumentOut, IngestOut
from app.db import repository as repo
from app.db.connection import get_connection
from app.ingestion.parsers import PARSERS, UnsupportedFormatError, parse_file
from app.ingestion.pipeline import ingest_document
from app.llm.agent import run_agent

MAX_UPLOAD_BYTES = 5 * 1024 * 1024   # 5 MB

app = FastAPI(title="AI Investigation Engine")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/documents", response_model=list[DocumentOut])
def list_documents(limit: int = 100, source_prefix: str = "upload://") -> list[dict]:
    with get_connection() as conn:
        docs = repo.list_documents(conn)
    docs = [d for d in docs if d["source"].startswith(source_prefix)]
    return docs[:limit]


@app.post("/documents", response_model=list[IngestOut])
async def upload_document(file: UploadFile = File(...), strategy: str = "sentence") -> list[IngestOut]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in PARSERS:
        raise HTTPException(415, f"Unsupported format: {suffix or 'none'}. Allowed: {sorted(PARSERS)}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 5 MB)")
    if strategy not in ("sentence", "fixed"):
        raise HTTPException(422, "strategy must be 'sentence' or 'fixed'")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / Path(file.filename).name
        path.write_bytes(data)
        try:
            docs = parse_file(path)
        except UnsupportedFormatError as e:
            raise HTTPException(415, str(e))
        except Exception as e:
            raise HTTPException(422, f"Could not parse file: {type(e).__name__}")

    results = []
    with get_connection() as conn:
        for doc in docs:
            doc.source = f"upload://{file.filename}" + (f"#{doc.source.split('#')[-1]}" if len(docs) > 1 else "")
            res = ingest_document(conn, doc, strategy=strategy)
            results.append(IngestOut(status=res.status, document_id=res.document_id, chunks=res.chunks))
    return results


@app.delete("/documents/{document_id}")
def delete_document(document_id: int) -> dict:
    with get_connection() as conn:
        ok = repo.delete_document(conn, document_id)
        conn.commit()
    if not ok:
        raise HTTPException(404, "Document not found")
    return {"deleted": document_id}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    with get_connection() as conn:
        a = run_agent(conn, req.question, mode=req.mode, rerank=False)
    if a.status == "error":
        raise HTTPException(503, a.missing)
    return AskResponse(
        status=a.status, answer=a.answer, citations=a.citations, conflicts=a.conflicts,
        missing=a.missing, sources=a.sources, trace=a.trace,
    )
import pytest

from app.db import repository as repo
from app.db.connection import get_connection
from app.ingestion.models import ParsedDocument
from app.ingestion.pipeline import ingest_document


def fake_embed(texts):
    return [[0.1] * 384 for _ in texts]


@pytest.fixture
def conn():
    c = get_connection()
    yield c
    c.execute("DELETE FROM documents WHERE source LIKE 'test://%'")
    c.commit()
    c.close()


def make_doc(text, source="test://doc1"):
    return ParsedDocument(title="T", source=source, format="txt", text=text)


def test_insert_duplicate_update_delete(conn):
    r1 = ingest_document(conn, make_doc("Alpha beta. Gamma delta."), embed=fake_embed)
    assert r1.status == "inserted" and r1.chunks >= 1

    r2 = ingest_document(conn, make_doc("Alpha beta. Gamma delta."), embed=fake_embed)
    assert r2.status == "duplicate"

    r3 = ingest_document(conn, make_doc("Totally new content here."), embed=fake_embed)
    assert r3.status == "updated" and r3.document_id == r1.document_id

    assert repo.delete_document(conn, r1.document_id) is True
    conn.commit()
    assert repo.find_by_source(conn, "test://doc1") is None
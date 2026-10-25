from app.llm.agent import _parse_json, validate
from app.llm.tools import EvidenceStore
from app.retrieval.models import Hit


def store_with(*texts):
    s = EvidenceStore()
    for i, t in enumerate(texts, 1):
        s.add(Hit(chunk_id=i, document_id=i, title=f"T{i}", source="s", content=t))
    return s


def test_valid_answer_keeps_real_citations_only():
    s = store_with("a", "b")
    r = validate({"status": "answered", "answer": "x [1]", "citations": [1, 99]}, s)
    assert r.status == "answered" and r.citations == [1]


def test_answer_without_citation_becomes_insufficient():
    r = validate({"status": "answered", "answer": "x", "citations": [42]}, store_with("a"))
    assert r.status == "insufficient_evidence"


def test_conflict_requires_description():
    r = validate({"status": "conflict", "citations": [1], "conflicts": []}, store_with("a"))
    assert r.status == "insufficient_evidence"


def test_unknown_status_is_safe():
    r = validate({"status": "weird"}, store_with("a"))
    assert r.status == "insufficient_evidence"


def test_evidence_store_dedups_chunks():
    s = EvidenceStore()
    h = Hit(1, 1, "t", "s", "c")
    assert s.add(h) == s.add(h) == 1


def test_parse_json_handles_fences_and_garbage():
    assert _parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _parse_json("not json") == {}
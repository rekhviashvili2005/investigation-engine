import pytest

from app.ingestion.chunking import chunk_text, fixed_chunks, sentence_chunks


def test_fixed_size_and_overlap():
    text = "a" * 1000
    chunks = fixed_chunks(text, size=300, overlap=50)
    assert all(len(c.text) <= 300 for c in chunks)
    assert chunks[1].start_char == chunks[0].end_char - 50


def test_fixed_empty():
    assert fixed_chunks("") == []


def test_fixed_bad_params():
    with pytest.raises(ValueError):
        fixed_chunks("abc", size=10, overlap=10)


def test_sentence_boundaries_respected():
    text = "First sentence here. Second one follows. Third is last."
    chunks = sentence_chunks(text, max_chars=45, overlap_sentences=0)
    assert all(c.text.endswith(".") for c in chunks)


def test_sentence_overlap():
    text = "One two. Three four. Five six. Seven eight."
    chunks = sentence_chunks(text, max_chars=20, overlap_sentences=1)
    assert "Three four." in chunks[0].text + chunks[1].text
    assert len(chunks) >= 2


def test_unknown_strategy():
    with pytest.raises(ValueError):
        chunk_text("x", strategy="nope")
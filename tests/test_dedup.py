from app.ingestion.dedup import content_hash, is_near_duplicate


def test_same_hash_ignores_whitespace_and_case():
    assert content_hash("Hello   World") == content_hash("hello world")


def test_different_hash():
    assert content_hash("a") != content_hash("b")


def test_near_duplicate():
    a = "the quick brown fox jumps over the lazy dog near the river bank today"
    b = "the quick brown fox jumps over the lazy dog near the river bank now"
    assert is_near_duplicate(a, b, threshold=0.6)
    assert not is_near_duplicate(a, "completely different text about something else entirely here")
from app.retrieval.bm25 import bm25_scores, tokenize
from app.retrieval.fusion import rrf_fuse
from app.retrieval.models import Hit
from app.retrieval.rerank import mmr_rerank


def hit(i, doc, text, score=1.0):
    return Hit(chunk_id=i, document_id=doc, title="t", source="s", content=text, score=score)


def test_tokenize_drops_stopwords():
    assert tokenize("The Eiffel Tower is in Paris") == ["eiffel", "tower", "paris"]


def test_bm25_prefers_rarer_term_and_more_matches():
    docs = [tokenize("paris eiffel tower"), tokenize("paris paris city"), tokenize("london bridge")]
    doc_freq = {"eiffel": 1, "paris": 2}
    scores = bm25_scores(["eiffel", "paris"], docs, doc_freq, n_docs=3, avg_len=3.0)
    assert scores[0] > scores[1] > scores[2] == 0.0


def test_rrf_rewards_agreement():
    a = [hit(1, 1, "x"), hit(2, 2, "y"), hit(3, 3, "z")]
    b = [hit(2, 2, "y"), hit(4, 4, "w"), hit(1, 1, "x")]
    fused = rrf_fuse([a, b], top_n=4)
    assert fused[0].chunk_id in (1, 2)          # ორივე სიაში მაღლა არიან
    assert {h.chunk_id for h in fused} == {1, 2, 3, 4}


def test_mmr_limits_per_document():
    hits = [hit(1, 1, "alpha beta gamma delta", 1.0),
            hit(2, 1, "alpha beta gamma epsilon", 0.9),
            hit(3, 2, "totally different words here now", 0.5)]
    out = mmr_rerank(hits, k=3, max_per_doc=1)
    assert [h.document_id for h in out] == [1, 2]


def test_mmr_empty():
    assert mmr_rerank([]) == []
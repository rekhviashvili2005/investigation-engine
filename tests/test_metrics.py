from eval.metrics import full_hit_at_k, recall_at_k, reciprocal_rank


def test_recall():
    assert recall_at_k(["a", "b", "c"], {"a", "c"}, 2) == 0.5
    assert recall_at_k(["a", "b", "c"], {"a", "c"}, 3) == 1.0
    assert recall_at_k([], {"a"}, 5) == 0.0


def test_mrr():
    assert reciprocal_rank(["x", "a"], {"a"}) == 0.5
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_full_hit():
    assert full_hit_at_k(["a", "b"], {"a", "b"}, 2) == 1.0
    assert full_hit_at_k(["a", "x"], {"a", "b"}, 2) == 0.0
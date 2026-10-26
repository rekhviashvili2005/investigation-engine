from eval.answer_metrics import answer_correct, citation_accuracy


def test_answer_correct():
    assert answer_correct("Yes, both were American [1][8].", "yes")
    assert answer_correct("She was Chief of Protocol.", "Chief of Protocol")
    assert not answer_correct("No.", "yes")
    assert not answer_correct("Yesterday", "yes")


def test_citation_accuracy():
    assert citation_accuracy(["A", "B", "X"], ["A", "B"]) == 1.0
    assert citation_accuracy(["A"], ["A", "B"]) == 0.5
    assert citation_accuracy([], ["A"]) == 0.0
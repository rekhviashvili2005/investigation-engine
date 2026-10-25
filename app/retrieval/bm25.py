import math
import re
from collections import Counter

import psycopg

from app.retrieval.models import Hit

_TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "is",
    "are", "was", "were", "by", "with", "as", "that", "this", "it", "its",
    "from", "which", "who", "what", "when", "where", "did", "does", "do",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def bm25_scores(
    query_terms: list[str],
    docs: list[list[str]],
    doc_freq: dict[str, int],
    n_docs: int,
    avg_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """სუფთა BM25 (ბაზის გარეშე, ადვილად ტესტირებადი).

    score(D,Q) = sum_t IDF(t) * tf*(k1+1) / (tf + k1*(1 - b + b*|D|/avgdl))
    IDF(t)     = ln(1 + (N - n_t + 0.5) / (n_t + 0.5))
    """
    scores = []
    for tokens in docs:
        tf = Counter(tokens)
        length = len(tokens) or 1
        score = 0.0
        for term in set(query_terms):
            f = tf.get(term, 0)
            if f == 0:
                continue
            n_t = doc_freq.get(term, 0)
            idf = math.log(1 + (n_docs - n_t + 0.5) / (n_t + 0.5))
            denom = f + k1 * (1 - b + b * length / avg_len)
            score += idf * f * (k1 + 1) / denom
        scores.append(score)
    return scores


def _collection_stats(conn: psycopg.Connection, terms: list[str]) -> tuple[int, float, dict[str, int]]:
    """N, საშუალო სიგრძე და თითო სიტყვის document frequency მთელი კოლექციიდან."""
    n_docs, avg_len = conn.execute(
        "SELECT count(*), coalesce(avg(array_length(string_to_array(content, ' '), 1)), 1) FROM chunks"
    ).fetchone()
    doc_freq: dict[str, int] = {}
    for term in terms:
        row = conn.execute(
            "SELECT count(*) FROM chunks WHERE tsv @@ plainto_tsquery('english', %s)", (term,)
        ).fetchone()
        doc_freq[term] = row[0]
    return n_docs, float(avg_len), doc_freq


def bm25_search(conn: psycopg.Connection, query: str, k: int = 20, candidates: int = 300) -> list[Hit]:
    terms = tokenize(query)
    if not terms:
        return []

    # 1) კანდიდატები GIN ინდექსით (OR ლოგიკა: ერთი სიტყვაც საკმარისია)
    tsquery = " | ".join(terms)
    rows = conn.execute(
        """SELECT c.id, c.document_id, d.title, d.source, c.content
           FROM chunks c JOIN documents d ON d.id = c.document_id
           WHERE c.tsv @@ to_tsquery('english', %s)
           LIMIT %s""",
        (tsquery, candidates),
    ).fetchall()
    if not rows:
        return []

    # 2) BM25 ქულები ჩვენივე ფორმულით
    n_docs, avg_len, doc_freq = _collection_stats(conn, terms)
    tokenized = [tokenize(r[4]) for r in rows]
    scores = bm25_scores(terms, tokenized, doc_freq, n_docs, avg_len)

    hits = [
        Hit(chunk_id=r[0], document_id=r[1], title=r[2], source=r[3], content=r[4], score=s)
        for r, s in zip(rows, scores)
    ]
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:k]
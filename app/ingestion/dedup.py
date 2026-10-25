import hashlib
import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def content_hash(text: str) -> str:
    """ზუსტი დუბლიკატი: ნორმალიზებული ტექსტის SHA-256."""
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def shingles(text: str, k: int = 5) -> set[str]:
    words = normalize(text).split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def is_near_duplicate(text_a: str, text_b: str, threshold: float = 0.8) -> bool:
    """თითქმის დუბლიკატი: 5-სიტყვიანი shingle-ების Jaccard მსგავსება."""
    return jaccard(shingles(text_a), shingles(text_b)) >= threshold
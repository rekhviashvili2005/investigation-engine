"""პასუხის მეტრიკები (LLM-ისა და ბაზის გარეშე)."""
import re
import string


def normalize(text: str) -> str:
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def answer_correct(predicted: str, expected: str) -> bool:
    """მოსალოდნელი პასუხი შედის ნორმალიზებულ პასუხში (სიტყვების საზღვრებით)."""
    p, e = normalize(predicted), normalize(expected)
    if not e:
        return False
    return re.search(rf"\b{re.escape(e)}\b", p) is not None


def citation_accuracy(cited_titles: list[str], supporting: list[str]) -> float:
    """supporting პარაგრაფებიდან რამდენი არის ციტირებულში (0..1)."""
    if not supporting:
        return 0.0
    return len(set(supporting) & set(cited_titles)) / len(set(supporting))
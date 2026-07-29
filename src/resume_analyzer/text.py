from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z][a-z0-9+#.-]{1,}")
_STOP = {"about", "after", "all", "also", "and", "any", "are", "been", "but", "can", "for", "from", "has", "have", "into", "its", "more", "our", "that", "the", "their", "this", "through", "using", "was", "were", "will", "with", "work", "you", "your"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\ufeff", " ")).strip()


def tokens(text: str) -> list[str]:
    return [word for word in _TOKEN.findall(text.lower()) if word not in _STOP and len(word) > 2]


def cosine_similarity(left: str, right: str) -> float:
    """TF-IDF cosine over two documents; transparent and dependency-free."""
    left_counts, right_counts = Counter(tokens(left)), Counter(tokens(right))
    vocabulary = set(left_counts) | set(right_counts)
    if not vocabulary:
        return 0.0
    # With two documents, rare terms receive more weight than shared boilerplate.
    left_vector, right_vector = {}, {}
    for term in vocabulary:
        df = int(term in left_counts) + int(term in right_counts)
        idf = math.log((1 + 2) / (1 + df)) + 1
        left_vector[term] = left_counts[term] * idf
        right_vector[term] = right_counts[term] * idf
    dot = sum(left_vector[t] * right_vector[t] for t in vocabulary)
    norm_left = math.sqrt(sum(value * value for value in left_vector.values()))
    norm_right = math.sqrt(sum(value * value for value in right_vector.values()))
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0


def keyword_gaps(resume: str, job: str, limit: int = 12) -> list[str]:
    resume_terms = set(tokens(resume))
    counts = Counter(tokens(job))
    return [term for term, _ in counts.most_common() if term not in resume_terms and len(term) > 3][:limit]


def redact_personal_data(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        candidate = line.strip()
        words = candidate.split()
        if 2 <= len(words) <= 5 and re.fullmatch(r"[A-Za-z .'-]+", candidate) and (candidate.isupper() or candidate.istitle()):
            lines[index] = "[NAME]"
            break
    text = "\n".join(lines)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    text = re.sub(r"(?:\+?\d[\d ()-]{7,}\d)", "[PHONE]", text)
    text = re.sub(r"https?://\S+|(?:www\.)\S+", "[URL]", text)
    return text

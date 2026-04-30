"""
Trend keyword extraction utilities.

Two methods supported:
  - TF-IDF: pure-python, no sklearn dependency. Term frequency within the filtered
    subset, weighted by inverse document frequency over the full corpus.
  - KeyBERT-style (BERT): candidate terms scored by cosine similarity between their
    Ollama embedding and the centroid embedding of the filtered subset.
"""
import math
import re
from collections import Counter
from typing import Iterable

import numpy as np

from backend.utils.embeddings import embed_text, embed_record


# Common English stopwords + scientific filler words
STOPWORDS: set[str] = {
    "the", "and", "for", "with", "this", "that", "these", "those", "from",
    "into", "onto", "than", "then", "such", "very", "also", "both", "either",
    "neither", "between", "among", "while", "when", "where", "which", "what",
    "whose", "whom", "their", "there", "they", "them", "have", "has", "had",
    "having", "been", "being", "were", "was", "are", "will", "would", "should",
    "could", "may", "might", "must", "can", "not", "but", "nor", "yet", "any",
    "all", "some", "few", "many", "much", "more", "most", "less", "least",
    "our", "ours", "your", "yours", "his", "her", "hers", "its", "itself",
    "himself", "herself", "themselves", "ourselves",
    # paper boilerplate
    "paper", "study", "studies", "result", "results", "show", "shows", "shown",
    "propose", "proposed", "proposes", "present", "presents", "presented",
    "novel", "new", "based", "using", "use", "used", "uses", "method", "methods",
    "approach", "approaches", "model", "models", "system", "systems", "data",
    "analysis", "performance", "framework", "frameworks", "task", "tasks",
    "work", "works", "research", "demonstrate", "demonstrates", "achieve",
    "achieves", "achieved", "obtain", "obtained", "evaluate", "evaluated",
    "experimental", "experiment", "experiments", "compared", "compare",
    "introduction", "conclusion", "abstract", "section", "figure", "table",
    "et", "al", "etc", "via", "however", "therefore", "thus", "hence",
    "respectively", "given", "shown", "well", "across", "within", "without",
    "high", "low", "large", "small", "good", "better", "best", "different",
    "various", "similar", "several", "specific", "general", "important",
    "significant", "potential", "current", "previous", "recent", "future",
    "first", "second", "third", "two", "three", "four", "one",
}


_TOKEN_RE = re.compile(r"[a-z][a-z0-9\-]{1,}")


def tokenize(text: str) -> list[str]:
    """Lowercase, strip non-alpha, drop short tokens and stopwords."""
    if not text:
        return []
    return [
        t for t in _TOKEN_RE.findall(text.lower())
        if len(t) >= 3 and t not in STOPWORDS
    ]


def ngrams(tokens: list[str], n: int) -> list[str]:
    if n <= 1:
        return tokens
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def doc_terms(title: str, abstract: str | None) -> list[str]:
    """Return uni- and bi-grams for a single document (title + abstract)."""
    toks = tokenize(f"{title or ''} {abstract or ''}")
    return ngrams(toks, 1) + ngrams(toks, 2)


# ── TF-IDF ────────────────────────────────────────────────────────────────────

def tfidf_keywords(
    subset_docs: list[dict],
    corpus_docs: list[dict],
    top_k: int = 20,
    min_tf: int = 2,
) -> list[dict]:
    """
    TF over `subset_docs`, IDF over `corpus_docs` (typically the full table).
    Returns [{term, score, tf, df}, ...] sorted by score desc.
    """
    tf: Counter[str] = Counter()
    for d in subset_docs:
        tf.update(set(doc_terms(d.get("title", ""), d.get("abstract"))))

    df: Counter[str] = Counter()
    n_corpus = 0
    for d in corpus_docs:
        df.update(set(doc_terms(d.get("title", ""), d.get("abstract"))))
        n_corpus += 1

    out = []
    for term, freq in tf.items():
        if freq < min_tf:
            continue
        idf = math.log((n_corpus + 1) / (df.get(term, 0) + 1)) + 1.0
        out.append({
            "term": term,
            "score": round(freq * idf, 3),
            "tf": freq,
            "df": df.get(term, 0),
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top_k]


# ── KeyBERT-style (BERT embeddings) ───────────────────────────────────────────

def keybert_keywords(
    subset_docs: list[dict],
    top_k: int = 20,
    candidate_pool: int = 60,
    min_tf: int = 2,
) -> tuple[list[dict], list[tuple[int, bytes]]]:
    """
    1) Build a candidate pool of high-frequency uni/bi-grams from the subset.
    2) Compute the L2-normalized centroid of doc embeddings.
    3) Score each candidate by cosine(candidate_embedding, centroid).

    Returns (keywords, fresh_embeddings) where fresh_embeddings is a list of
    (doc_id, vector_bytes) for documents whose embeddings were computed during
    this call — caller can persist them to the DB.
    Returns ([], []) if Ollama is unavailable.
    """
    # 1. Frequency-based candidates
    tf: Counter[str] = Counter()
    for d in subset_docs:
        tf.update(doc_terms(d.get("title", ""), d.get("abstract")))
    candidates = [t for t, c in tf.most_common(candidate_pool) if c >= min_tf]
    if not candidates:
        return [], []

    # 2. Centroid from cached or freshly computed doc embeddings
    vecs: list[np.ndarray] = []
    fresh: list[tuple[int, bytes]] = []
    for d in subset_docs:
        blob = d.get("embedding")
        if blob:
            vecs.append(np.frombuffer(bytes(blob), dtype=np.float32))
            continue
        v = embed_record(d.get("title", ""), d.get("abstract") or "")
        if v is None:
            continue
        vecs.append(v)
        if d.get("id") is not None:
            fresh.append((d["id"], v.tobytes()))

    if not vecs:
        return [], fresh

    mat = np.stack(vecs)
    centroid = mat.mean(axis=0)
    norm = np.linalg.norm(centroid) or 1.0
    centroid = centroid / norm

    # 3. Score candidates
    scored: list[dict] = []
    for term in candidates:
        v = embed_text(term)
        if v is None:
            continue
        n = np.linalg.norm(v) or 1.0
        sim = float(np.dot(v / n, centroid))
        scored.append({
            "term": term,
            "score": round(sim, 4),
            "tf": tf[term],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k], fresh

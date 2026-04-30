"""
Keyword frequency analysis using TF-IDF on paper titles and abstracts.
Produces top-term rankings and year-over-year trend data.

Upgrade path: replace TF-IDF vectorizer with sentence-transformers
(e.g. 'all-MiniLM-L6-v2') for BERT-level semantic clustering.
"""
import re
from collections import defaultdict, Counter
from typing import List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "this", "that", "these",
    "those", "we", "our", "us", "it", "its", "than", "which", "also",
    "as", "using", "based", "paper", "study", "research", "method",
    "approach", "results", "show", "proposed", "present", "novel",
    "new", "two", "three", "one", "via", "into", "over", "under",
    "both", "such", "each", "while", "however", "thus", "due", "use",
    "used", "well", "high", "low", "large", "small", "different",
    "various", "without", "between", "among", "then", "they", "their",
    "not", "more", "than", "most", "many",
}


def _clean_text(text: str) -> str:
    return re.sub(r"[^a-zA-Z\s]", " ", text.lower())


def analyze(papers: List[Any]) -> Dict:
    """
    Run TF-IDF + frequency analysis on a list of Paper ORM objects.
    Returns top_keywords, yearly_trend, stats.
    """
    if not papers:
        return {
            "top_keywords": [],
            "yearly_trend": [],
            "top5_words": [],
            "total_papers": 0,
            "year_range": [None, None],
            "avg_citations": 0,
        }

    texts = []
    for p in papers:
        txt = p.title or ""
        if p.abstract:
            txt += " " + p.abstract
        texts.append(_clean_text(txt))

    # ── TF-IDF top terms ──────────────────────────────────────────────
    top_keywords = []
    try:
        vec = TfidfVectorizer(
            max_features=60,
            stop_words=list(STOPWORDS),
            ngram_range=(1, 2),
            min_df=max(2, len(texts) // 20),
        )
        tfidf = vec.fit_transform(texts)
        names = vec.get_feature_names_out()
        scores = tfidf.mean(axis=0).A1
        pairs = sorted(zip(names, scores.tolist()), key=lambda x: x[1], reverse=True)
        top_keywords = [{"word": w, "score": round(s, 5)} for w, s in pairs[:30]]
    except Exception:
        # Fallback: simple frequency if TF-IDF fails (too few docs)
        all_words: Counter = Counter()
        for txt in texts:
            words = [w for w in txt.split() if len(w) > 3 and w not in STOPWORDS]
            all_words.update(words)
        top_keywords = [
            {"word": w, "score": round(c / len(texts), 5)}
            for w, c in all_words.most_common(30)
        ]

    # ── Year-over-year word frequency ────────────────────────────────
    yearly_raw: Dict[int, Counter] = defaultdict(Counter)
    for paper in papers:
        if not paper.year:
            continue
        txt = _clean_text(f"{paper.title or ''} {paper.abstract or ''}")
        words = [w for w in txt.split() if len(w) > 3 and w not in STOPWORDS]
        yearly_raw[paper.year].update(words)

    all_words_total: Counter = Counter()
    for c in yearly_raw.values():
        all_words_total.update(c)
    top5 = [w for w, _ in all_words_total.most_common(5)]

    years = sorted(yearly_raw.keys())
    yearly_trend = [
        {
            "year": yr,
            **{word: yearly_raw[yr].get(word, 0) for word in top5},
        }
        for yr in years
    ]

    # ── Stats ────────────────────────────────────────────────────────
    citations = [p.citation_count or 0 for p in papers]
    paper_years = [p.year for p in papers if p.year]

    return {
        "top_keywords": top_keywords,
        "yearly_trend": yearly_trend,
        "top5_words": top5,
        "total_papers": len(papers),
        "year_range": [min(paper_years) if paper_years else None,
                       max(paper_years) if paper_years else None],
        "avg_citations": round(sum(citations) / len(citations), 1) if citations else 0,
    }

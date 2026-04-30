"""
/api/insights/emerging  — papers/patents rising fast by citation velocity
/api/insights/network   — similarity graph nodes + edges for D3 visualization
"""
import math
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Query
import numpy as np

from backend.config import DB_PATH
from backend.db.schema import get_connection
from backend.utils.text_utils import clean_assignee
from backend.utils.text_analysis import tfidf_keywords, keybert_keywords

router = APIRouter(prefix="/api/insights", tags=["insights"])


# ── emergence detection ───────────────────────────────────────────────────────

def _emergence_score(citation_count: int, published_date: str) -> float:
    """
    Score = log(1 + citations) / log(1 + days_since_publication)
    High score = many citations, published recently → hot topic.
    """
    try:
        pub = datetime.strptime(published_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days = max(1, (datetime.now(timezone.utc) - pub).days)
        return math.log1p(citation_count) / math.log1p(days)
    except (ValueError, TypeError):
        return 0.0


@router.get("/emerging")
def emerging_papers(
    domain: str = Query("", description="Filter by domain_tag"),
    days:   int = Query(365, description="Consider papers published within this many days"),
    limit:  int = Query(20, ge=1, le=100),
    type:   str = Query("papers", description="papers | patents"),
):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    if type == "papers":
        where = "published_date >= ? AND citation_count > 0"
        params: list = [since]
        if domain:
            where += " AND domain_tag = ?"
            params.append(domain)
        sql = (
            f"SELECT id, title, abstract, authors, source, doi, citation_count, "
            f"published_date, domain_tag, journal "
            f"FROM papers WHERE {where} ORDER BY citation_count DESC LIMIT 500"
        )
    else:
        where = "publication_date >= ?"
        params = [since]
        if domain:
            where += " AND domain_tag = ?"
            params.append(domain)
        sql = (
            f"SELECT id, patent_number, title, abstract, assignee, inventors, "
            f"ipc_codes, filing_date, publication_date, source, country, domain_tag "
            f"FROM patents WHERE {where} ORDER BY publication_date DESC LIMIT 500"
        )

    with get_connection(DB_PATH) as conn:
        rows = conn.execute(sql, params).fetchall()

    if type == "papers":
        scored = sorted(
            [dict(r) for r in rows],
            key=lambda r: _emergence_score(r["citation_count"] or 0, r["published_date"] or ""),
            reverse=True,
        )
        for item in scored:
            item["emergence_score"] = round(
                _emergence_score(item["citation_count"] or 0, item["published_date"] or ""), 4
            )
    else:
        scored = [dict(r) for r in rows]
        for item in scored:
            item["assignee"]  = clean_assignee(item.get("assignee", ""))
            item["emergence_score"] = 0.0

    return {"items": scored[:limit], "total": len(rows)}


# ── network graph ─────────────────────────────────────────────────────────────

from backend.utils.embeddings import cosine_sim  # noqa: E402


@router.get("/network")
def network_graph(
    type:      str   = Query("papers"),
    domain:    str   = Query(""),
    limit:     int   = Query(80, ge=10, le=300),
    threshold: float = Query(0.75, description="Min cosine similarity for an edge"),
    balanced:  bool  = Query(True, description="Sample top-K per domain for even distribution"),
):
    """
    Returns {nodes, edges} for D3 force-directed graph.

    balanced=True (default): pick top K papers per domain so every domain is
    represented and within-domain edges are dense.
    balanced=False: top N globally by citation count.

    Embeddings are computed on-the-fly for nodes missing them and cached in DB.
    """
    from backend.utils.embeddings import embed_record

    table = "papers" if type == "papers" else "patents"

    # ── Node selection ────────────────────────────────────────────────────────
    if balanced and not domain:
        # Stratified: top K per domain
        with get_connection(DB_PATH) as conn:
            domains = [
                r[0] for r in conn.execute(
                    f"SELECT DISTINCT domain_tag FROM {table} ORDER BY domain_tag"
                ).fetchall()
            ]
        k = max(3, limit // max(len(domains), 1))
        rows_data = []
        for dtag in domains:
            if type == "papers":
                sql = (
                    "SELECT id, title, abstract, source, citation_count, published_date, "
                    "domain_tag, embedding FROM papers "
                    "WHERE domain_tag=? ORDER BY citation_count DESC LIMIT ?"
                )
            else:
                sql = (
                    "SELECT id, patent_number, title, abstract, source, publication_date, "
                    "domain_tag, assignee, country, embedding FROM patents "
                    "WHERE domain_tag=? ORDER BY publication_date DESC LIMIT ?"
                )
            with get_connection(DB_PATH) as conn:
                rows_data.extend([dict(r) for r in conn.execute(sql, (dtag, k)).fetchall()])
    else:
        where_parts = ["1=1"]
        params: list = []
        if domain:
            where_parts.append("domain_tag = ?")
            params.append(domain)
        where = " AND ".join(where_parts)
        if type == "papers":
            sql = (
                "SELECT id, title, abstract, source, citation_count, published_date, "
                f"domain_tag, embedding FROM papers WHERE {where} "
                "ORDER BY citation_count DESC LIMIT ?"
            )
        else:
            sql = (
                "SELECT id, patent_number, title, abstract, source, publication_date, "
                f"domain_tag, assignee, country, embedding FROM patents WHERE {where} "
                "ORDER BY publication_date DESC LIMIT ?"
            )
        with get_connection(DB_PATH) as conn:
            rows_data = [dict(r) for r in conn.execute(sql, [*params, limit]).fetchall()]

    if not rows_data:
        return {"nodes": [], "edges": [], "type": type, "embedded": 0}

    # ── Embedding: compute missing, cache in DB ────────────────────────────────
    embedded_now = 0
    for row in rows_data:
        if row.get("embedding"):
            continue
        vec = embed_record(row.get("title", ""), row.get("abstract") or "")
        if vec is None:
            raise HTTPException(
                503,
                detail="Ollama가 실행 중이지 않거나 nomic-embed-text 모델이 없어요. "
                       "`ollama pull nomic-embed-text` 후 Ollama를 실행하세요."
            )
        blob = vec.tobytes()
        with get_connection(DB_PATH) as conn:
            conn.execute(f"UPDATE {table} SET embedding=? WHERE id=?", (blob, row["id"]))
        row["embedding"] = blob
        embedded_now += 1

    # ── Build node list + embedding matrix ────────────────────────────────────
    nodes, vecs = [], []
    for row in rows_data:
        if not row.get("embedding"):
            continue
        d = {k: v for k, v in row.items() if k not in ("embedding", "abstract")}
        if type == "patents":
            d["assignee"] = clean_assignee(d.get("assignee", ""))
        nodes.append(d)
        vecs.append(np.frombuffer(bytes(row["embedding"]), dtype=np.float32))

    if not nodes:
        return {"nodes": [], "edges": [], "type": type, "embedded": 0}

    # ── Pairwise similarity → edges ───────────────────────────────────────────
    mat = np.stack(vecs)                          # (N, D)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1
    mat_norm = mat / norms
    sim_matrix = mat_norm @ mat_norm.T            # (N, N)  cosine similarities

    edges = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            sim = float(sim_matrix[i, j])
            if sim >= threshold:
                edges.append({
                    "source": nodes[i]["id"],
                    "target": nodes[j]["id"],
                    "weight": round(sim, 3),
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "type": type,
        "embedded": embedded_now,
        "domains": list({n["domain_tag"] for n in nodes}),
    }


# ── trend keyword analysis (TF-IDF / BERT) ────────────────────────────────────

@router.get("/trend-analysis")
def trend_analysis(
    method: str = Query("tfidf", description="tfidf | bert"),
    type:   str = Query("papers", description="papers | patents"),
    domain: str = Query("", description="Filter by domain_tag"),
    days:   int = Query(365, ge=7, le=3650),
    top_k:  int = Query(20, ge=5, le=50),
):
    """
    Keyword extraction over a filtered subset of the corpus.

    - tfidf: term frequency in subset × IDF over the entire table.
    - bert : KeyBERT-style — candidate n-grams ranked by cosine similarity
             to the centroid of subset document embeddings (Ollama).
    """
    if method not in ("tfidf", "bert"):
        raise HTTPException(400, detail="method must be 'tfidf' or 'bert'")
    if type not in ("papers", "patents"):
        raise HTTPException(400, detail="type must be 'papers' or 'patents'")

    table = "papers" if type == "papers" else "patents"
    date_col = "published_date" if type == "papers" else "publication_date"
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    where_parts = [f"{date_col} >= ?"]
    params: list = [since]
    if domain:
        where_parts.append("domain_tag = ?")
        params.append(domain)
    where = " AND ".join(where_parts)

    # subset: filtered docs (need embedding for bert)
    subset_cols = "id, title, abstract, domain_tag, embedding"
    with get_connection(DB_PATH) as conn:
        subset_rows = [
            dict(r) for r in conn.execute(
                f"SELECT {subset_cols} FROM {table} WHERE {where} "
                f"ORDER BY {date_col} DESC LIMIT 500",
                params,
            ).fetchall()
        ]

    if not subset_rows:
        return {
            "method": method, "type": type, "domain": domain, "days": days,
            "subset_size": 0, "keywords": [], "message": "조건에 해당하는 문서가 없습니다.",
        }

    if method == "tfidf":
        # IDF corpus: full table (titles + abstracts only, no embedding column)
        with get_connection(DB_PATH) as conn:
            corpus_rows = [
                dict(r) for r in conn.execute(
                    f"SELECT title, abstract FROM {table}"
                ).fetchall()
            ]
        keywords = tfidf_keywords(subset_rows, corpus_rows, top_k=top_k)
        return {
            "method": "tfidf",
            "type": type,
            "domain": domain,
            "days": days,
            "subset_size": len(subset_rows),
            "corpus_size": len(corpus_rows),
            "keywords": keywords,
        }

    # method == bert
    keywords, fresh = keybert_keywords(subset_rows, top_k=top_k)
    if not keywords:
        raise HTTPException(
            503,
            detail="Ollama 임베딩이 필요합니다. `ollama pull nomic-embed-text` 후 "
                   "Ollama를 실행하세요.",
        )
    # cache freshly computed doc embeddings back to DB
    if fresh:
        with get_connection(DB_PATH) as conn:
            for doc_id, blob in fresh:
                conn.execute(
                    f"UPDATE {table} SET embedding=? WHERE id=?",
                    (blob, doc_id),
                )

    return {
        "method": "bert",
        "type": type,
        "domain": domain,
        "days": days,
        "subset_size": len(subset_rows),
        "embedded_now": len(fresh),
        "keywords": keywords,
    }

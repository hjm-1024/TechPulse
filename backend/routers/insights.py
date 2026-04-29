"""
/api/insights/emerging  — papers/patents rising fast by citation velocity
/api/insights/network   — similarity graph nodes + edges for D3 visualization
"""
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
import numpy as np

from backend.config import DB_PATH
from backend.db.schema import get_connection
from backend.utils.text_utils import clean_assignee

router = APIRouter(prefix="/api/insights", tags=["insights"])


# ── emergence detection ───────────────────────────────────────────────────────

def _emergence_score(citation_count: int, published_date: str) -> float:
    """
    Score = log(1 + citations) / log(1 + days_since_publication)
    High score = many citations, published recently → hot topic.
    """
    try:
        pub = datetime.strptime(published_date[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0.0
    days = max(1, (datetime.utcnow() - pub).days)
    return math.log1p(citation_count) / math.log1p(days)


@router.get("/emerging")
def emerging_papers(
    domain: str = Query("", description="Filter by domain_tag"),
    days:   int = Query(365, description="Consider papers published within this many days"),
    limit:  int = Query(20, ge=1, le=100),
    type:   str = Query("papers", description="papers | patents"),
):
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

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
    limit:     int   = Query(80, ge=10, le=200),
    threshold: float = Query(0.82, description="Min cosine similarity for an edge"),
):
    """
    Returns {nodes, edges} for D3 force-directed graph.
    Nodes are the most-cited (papers) or most-recent (patents) documents.
    Embeddings are computed on-the-fly for any node that doesn't have one yet,
    then cached in the DB — so the first call is slower, subsequent calls are instant.
    """
    from backend.utils.embeddings import embed_record

    where_parts = ["1=1"]
    params: list = []
    if domain:
        where_parts.append("domain_tag = ?")
        params.append(domain)
    where = " AND ".join(where_parts)

    if type == "papers":
        sql = (
            "SELECT id, title, abstract, source, citation_count, published_date, domain_tag, embedding "
            f"FROM papers WHERE {where} ORDER BY citation_count DESC LIMIT ?"
        )
    else:
        sql = (
            "SELECT id, patent_number, title, abstract, source, publication_date, domain_tag, "
            "assignee, country, embedding "
            f"FROM patents WHERE {where} ORDER BY publication_date DESC LIMIT ?"
        )

    with get_connection(DB_PATH) as conn:
        rows = conn.execute(sql, [*params, limit]).fetchall()

    if not rows:
        return {"nodes": [], "edges": [], "type": type, "embedded": 0}

    table = "papers" if type == "papers" else "patents"

    # For rows missing embeddings, compute on-the-fly and cache
    embedded_now = 0
    rows_data = [dict(r) for r in rows]
    for row in rows_data:
        if row.get("embedding"):
            continue
        vec = embed_record(row.get("title", ""), row.get("abstract") or "")
        if vec is None:
            # Ollama not available — abort and tell the frontend
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

    # Build node list + embedding matrix
    nodes = []
    vecs  = []
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

    # Compute pairwise similarities → edges above threshold
    edges = []
    for i in range(len(vecs)):
        for j in range(i + 1, len(vecs)):
            sim = cosine_sim(vecs[i], vecs[j])
            if sim >= threshold:
                edges.append({
                    "source": nodes[i]["id"],
                    "target": nodes[j]["id"],
                    "weight": round(float(sim), 3),
                })

    return {"nodes": nodes, "edges": edges, "type": type, "embedded": embedded_now}

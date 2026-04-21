"""Semantic (vector) search endpoint using nomic-embed-text via Ollama."""

from fastapi import APIRouter, HTTPException
import numpy as np

from backend.config import DB_PATH
from backend.db.schema import get_connection
from backend.utils.embeddings import embed_text, cosine_sim

router = APIRouter()


def _load_vectors(table: str, domain: str, source: str) -> list[tuple]:
    """Load all rows that have an embedding, with optional filters."""
    wheres = ["embedding IS NOT NULL"]
    params: list = []
    if domain:
        wheres.append("domain_tag = ?")
        params.append(domain)
    if source:
        wheres.append("source = ?")
        params.append(source)
    where_sql = " AND ".join(wheres)

    if table == "papers":
        sql = (
            "SELECT id, title, abstract, authors, source, doi, citation_count, "
            "published_date, domain_tag, journal, embedding FROM papers"
            f" WHERE {where_sql}"
        )
    else:
        sql = (
            "SELECT id, patent_number, title, abstract, assignee, inventors, "
            "ipc_codes, filing_date, publication_date, source, country, domain_tag, embedding "
            f"FROM patents WHERE {where_sql}"
        )

    with get_connection(DB_PATH) as conn:
        return conn.execute(sql, params).fetchall()


@router.get("/api/search/semantic")
def semantic_search(
    q: str = "",
    type: str = "papers",
    domain: str = "",
    source: str = "",
    limit: int = 20,
):
    if not q.strip():
        return {"items": [], "total": 0, "pages": 1}

    query_vec = embed_text(q)
    if query_vec is None:
        raise HTTPException(503, detail="Ollama가 실행 중이지 않거나 nomic-embed-text 모델이 없어요.")

    rows = _load_vectors(type, domain, source)

    scored = []
    for row in rows:
        try:
            vec = np.frombuffer(bytes(row["embedding"]), dtype=np.float32)
            score = cosine_sim(query_vec, vec)
            d = {k: row[k] for k in row.keys() if k != "embedding"}
            d["similarity"] = round(float(score), 4)
            scored.append((score, d))
        except Exception:
            continue

    scored.sort(key=lambda x: -x[0])
    items = [r for _, r in scored[:limit]]

    return {"items": items, "total": len(items), "pages": 1}

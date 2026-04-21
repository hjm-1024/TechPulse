"""Semantic search, similar-document, and cross-type linking endpoints."""

from fastapi import APIRouter, HTTPException
import numpy as np

from backend.config import DB_PATH
from backend.db.schema import get_connection
from backend.utils.embeddings import cosine_sim, embed_text
from backend.utils.text_utils import clean_assignee, clean_inventors

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


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_embedding(table: str, doc_id: int) -> "np.ndarray | None":
    with get_connection(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT embedding FROM {table} WHERE id = ?", (doc_id,)
        ).fetchone()
    if row and row["embedding"]:
        return np.frombuffer(bytes(row["embedding"]), dtype=np.float32)
    return None


def _score_all(query_vec: np.ndarray, table: str, exclude_id: int,
               limit: int) -> list[dict]:
    if table == "papers":
        sql = ("SELECT id, title, abstract, authors, source, doi, citation_count, "
               "published_date, domain_tag, journal, embedding FROM papers "
               "WHERE embedding IS NOT NULL AND id != ?")
    else:
        sql = ("SELECT id, patent_number, title, abstract, assignee, inventors, "
               "ipc_codes, filing_date, publication_date, source, country, domain_tag, embedding "
               "FROM patents WHERE embedding IS NOT NULL AND id != ?")

    with get_connection(DB_PATH) as conn:
        rows = conn.execute(sql, (exclude_id,)).fetchall()

    scored = []
    for row in rows:
        try:
            vec = np.frombuffer(bytes(row["embedding"]), dtype=np.float32)
            score = cosine_sim(query_vec, vec)
            d = {k: row[k] for k in row.keys() if k != "embedding"}
            if table == "patents":
                d["assignee"] = clean_assignee(d.get("assignee", ""))
                d["inventors"] = clean_inventors(d.get("inventors", ""))
            d["similarity"] = round(float(score), 4)
            scored.append((score, d))
        except Exception:
            continue

    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]]


# ── similar documents (same type) ────────────────────────────────────────────

@router.get("/api/similar")
def find_similar(type: str = "papers", id: int = 0, limit: int = 5):
    """Return top-N most similar documents of the same type."""
    table = "papers" if type == "papers" else "patents"
    vec = _get_embedding(table, id)
    if vec is None:
        raise HTTPException(404, detail="해당 문서의 임베딩이 없어요. --embed 먼저 실행하세요.")
    items = _score_all(vec, table, exclude_id=id, limit=limit)
    return {"items": items}


# ── cross-type linking (paper → patents, patent → papers) ────────────────────

@router.get("/api/cross")
def cross_link(from_type: str, from_id: int, to_type: str, limit: int = 4):
    """Find documents of to_type most similar to a from_type document."""
    from_table = "papers" if from_type == "papers" else "patents"
    to_table   = "papers" if to_type  == "papers" else "patents"

    vec = _get_embedding(from_table, from_id)
    if vec is None:
        raise HTTPException(404, detail="임베딩 없음.")

    with get_connection(DB_PATH) as conn:
        if to_table == "papers":
            sql = ("SELECT id, title, abstract, authors, source, doi, citation_count, "
                   "published_date, domain_tag, journal, embedding "
                   "FROM papers WHERE embedding IS NOT NULL")
        else:
            sql = ("SELECT id, patent_number, title, abstract, assignee, inventors, "
                   "ipc_codes, filing_date, publication_date, source, country, domain_tag, embedding "
                   "FROM patents WHERE embedding IS NOT NULL")
        rows = conn.execute(sql).fetchall()

    scored = []
    for row in rows:
        try:
            rv = np.frombuffer(bytes(row["embedding"]), dtype=np.float32)
            score = cosine_sim(vec, rv)
            d = {k: row[k] for k in row.keys() if k != "embedding"}
            if to_table == "patents":
                d["assignee"] = clean_assignee(d.get("assignee", ""))
                d["inventors"] = clean_inventors(d.get("inventors", ""))
            d["similarity"] = round(float(score), 4)
            scored.append((score, d))
        except Exception:
            continue

    scored.sort(key=lambda x: -x[0])
    return {"items": [r for _, r in scored[:limit]]}

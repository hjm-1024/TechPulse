"""
/api/config/keywords  — CRUD for collection keywords
/api/config/stats     — per-keyword paper/patent counts + last collected
/api/config/domains   — list distinct domain_tags
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.config import DB_PATH
from backend.db.schema import get_connection
from backend.db.config_schema import get_all_keywords

router = APIRouter(prefix="/api/config", tags=["config"])


# ── stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def collection_stats():
    """Full overview: each keyword with paper count, patent count, sources, dates."""
    keywords = get_all_keywords(DB_PATH)
    if not keywords:
        return []

    with get_connection(DB_PATH) as conn:
        # Paper counts per keyword (title/abstract LIKE keyword)
        paper_rows = conn.execute(
            "SELECT domain_tag, COUNT(*) as cnt FROM papers GROUP BY domain_tag"
        ).fetchall()
        patent_rows = conn.execute(
            "SELECT domain_tag, COUNT(*) as cnt FROM patents GROUP BY domain_tag"
        ).fetchall()
        # Date ranges
        paper_dates = conn.execute(
            "SELECT domain_tag, MIN(published_date) as min_d, MAX(published_date) as max_d "
            "FROM papers GROUP BY domain_tag"
        ).fetchall()
        patent_dates = conn.execute(
            "SELECT domain_tag, MIN(publication_date) as min_d, MAX(publication_date) as max_d "
            "FROM patents GROUP BY domain_tag"
        ).fetchall()
        # Source breakdown
        source_rows = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM papers GROUP BY source"
        ).fetchall()
        patent_src = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM patents GROUP BY source"
        ).fetchall()

    paper_by_domain  = {r["domain_tag"]: r["cnt"] for r in paper_rows}
    patent_by_domain = {r["domain_tag"]: r["cnt"] for r in patent_rows}
    paper_date_by_domain  = {r["domain_tag"]: (r["min_d"], r["max_d"]) for r in paper_dates}
    patent_date_by_domain = {r["domain_tag"]: (r["min_d"], r["max_d"]) for r in patent_dates}

    result = []
    seen_domains: set[str] = set()
    for kw in keywords:
        tag = kw["domain_tag"]
        row = dict(kw)
        row["paper_count"]  = paper_by_domain.get(tag, 0)  if tag not in seen_domains else None
        row["patent_count"] = patent_by_domain.get(tag, 0) if tag not in seen_domains else None
        row["paper_date_range"]  = paper_date_by_domain.get(tag)
        row["patent_date_range"] = patent_date_by_domain.get(tag)
        seen_domains.add(tag)
        result.append(row)

    summary = {
        "keywords": result,
        "paper_sources":  [{"source": r["source"], "count": r["cnt"]} for r in source_rows],
        "patent_sources": [{"source": r["source"], "count": r["cnt"]} for r in patent_src],
        "totals": {
            "papers":  sum(paper_by_domain.values()),
            "patents": sum(patent_by_domain.values()),
        },
    }
    return summary


# ── keyword CRUD ──────────────────────────────────────────────────────────────

class KeywordCreate(BaseModel):
    keyword: str
    domain_tag: str
    sources: str = "arxiv,semantic_scholar,openalex,epo"
    days_back: int = 365


class KeywordUpdate(BaseModel):
    active: int | None = None
    domain_tag: str | None = None
    sources: str | None = None
    days_back: int | None = None


@router.get("/keywords")
def list_keywords():
    return get_all_keywords(DB_PATH)


@router.post("/keywords", status_code=201)
def add_keyword(body: KeywordCreate):
    try:
        with get_connection(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO collection_config (keyword, domain_tag, sources, days_back) "
                "VALUES (?, ?, ?, ?)",
                (body.keyword.strip(), body.domain_tag, body.sources, body.days_back),
            )
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(409, detail=f"키워드 '{body.keyword}' 이미 존재해요.")
        raise
    return {"ok": True}


@router.patch("/keywords/{kw_id}")
def update_keyword(kw_id: int, body: KeywordUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, detail="변경할 값이 없어요.")
    set_clause = ", ".join(f"{k}=?" for k in updates)
    with get_connection(DB_PATH) as conn:
        conn.execute(
            f"UPDATE collection_config SET {set_clause} WHERE id=?",
            [*updates.values(), kw_id],
        )
    return {"ok": True}


@router.delete("/keywords/{kw_id}")
def delete_keyword(kw_id: int):
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM collection_config WHERE id=?", (kw_id,))
    return {"ok": True}


@router.get("/domains")
def list_domains():
    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT DISTINCT domain_tag FROM collection_config ORDER BY domain_tag"
        ).fetchall()
    return [r["domain_tag"] for r in rows]

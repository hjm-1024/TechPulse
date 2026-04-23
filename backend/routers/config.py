"""
/api/config/keywords           — CRUD for collection keywords
/api/config/keywords/by-domain — keywords grouped by domain (for UI)
/api/config/keywords/expand    — Ollama-powered keyword expansion
/api/config/stats              — per-keyword paper/patent counts + last collected
/api/config/domains            — list distinct domain_tags
"""
import json
import os
import requests as _requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.config import DB_PATH
from backend.db.schema import get_connection
from backend.db.config_schema import get_all_keywords, get_keywords_by_domain

OLLAMA_BASE   = "http://localhost:11434"
EXPAND_MODEL  = os.getenv("OLLAMA_EXPAND_MODEL", "qwen3:14b-q8_0")

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


# ── domain-grouped view ───────────────────────────────────────────────────────

@router.get("/keywords/by-domain")
def keywords_by_domain():
    """키워드를 도메인별로 그룹화하여 반환. 프론트 도메인 뷰 전용."""
    return get_keywords_by_domain(DB_PATH)


# ── AI keyword expansion ──────────────────────────────────────────────────────

class ExpandRequest(BaseModel):
    domain_tag: str
    count: int = 8


@router.post("/keywords/expand")
def expand_keywords(body: ExpandRequest):
    """
    Ollama LLM을 사용해 도메인에 맞는 새 키워드를 추천하고 DB에 추가.
    기존 키워드와 중복되지 않는 것만 삽입.
    """
    existing = get_all_keywords(DB_PATH)
    domain_kws = [r["keyword"] for r in existing if r["domain_tag"] == body.domain_tag]
    all_kws    = [r["keyword"] for r in existing]

    if not domain_kws:
        raise HTTPException(400, detail=f"도메인 '{body.domain_tag}'에 기존 키워드가 없습니다.")

    prompt = (
        f"You are an expert in emerging technology research.\n"
        f"Domain: '{body.domain_tag.replace('_', ' ')}'\n"
        f"Existing keywords already collected: {json.dumps(domain_kws)}\n\n"
        f"Generate {body.count} NEW English search keywords for academic papers and patents "
        f"in this domain that are NOT already in the existing list above.\n"
        f"Focus on specific sub-fields, techniques, materials, or systems.\n"
        f"Return ONLY a JSON array of strings. No explanation.\n"
        f"Example: [\"keyword one\", \"keyword two\"]"
    )

    try:
        resp = _requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": EXPAND_MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.4}},
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "").strip()
    except Exception as exc:
        raise HTTPException(503, detail=f"Ollama 연결 실패: {exc}")

    # strip markdown code fences if present
    if "```" in raw:
        raw = raw.split("```")[1]
        raw = raw.lstrip("json").strip()

    try:
        suggestions: list[str] = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(502, detail=f"LLM 응답 파싱 실패: {raw[:200]}")

    existing_lower = {k.lower() for k in all_kws}
    added, skipped = [], []

    with get_connection(DB_PATH) as conn:
        for kw in suggestions:
            kw = kw.strip()
            if not kw or kw.lower() in existing_lower:
                skipped.append(kw)
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO collection_config (keyword, domain_tag) VALUES (?, ?)",
                    (kw, body.domain_tag),
                )
                added.append(kw)
                existing_lower.add(kw.lower())
            except Exception:
                skipped.append(kw)

    return {"domain_tag": body.domain_tag, "added": added, "skipped": skipped}

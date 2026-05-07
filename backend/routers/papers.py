"""
/api/papers — paginated paper list with optional filters.
"""

from fastapi import APIRouter, Query
from backend.config import DB_PATH
from backend.db.schema import get_connection

router = APIRouter(tags=["papers"])


@router.get("/papers")
def list_papers(
    domain: str | None = Query(None),
    source: str | None = Query(None),
    q: str | None = Query(None, description="Search title/abstract"),
    sort_by: str = Query("citation_count", enum=["citation_count", "published_date"]),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    where_clauses: list[str] = []
    params: list = []

    if domain:
        where_clauses.append("domain_tag = ?")
        params.append(domain)
    if source:
        where_clauses.append("source = ?")
        params.append(source)
    if q:
        where_clauses.append("(title LIKE ? OR abstract LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    order = "DESC" if sort_by == "citation_count" else "DESC"

    offset = (page - 1) * page_size

    with get_connection(DB_PATH) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM papers {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT id, title, authors, published_date, source,
                   doi, citation_count, journal, domain_tag
            FROM papers
            {where}
            ORDER BY {sort_by} {order}
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": -(-total // page_size),  # ceiling division
        "items": [dict(r) for r in rows],
    }

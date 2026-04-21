"""
/api/patents/summary  — counts by source × domain
/api/patents/trend    — monthly filing/publication trend by domain
/api/patents/list     — paginated patent list with filters
/api/patents/top      — top assignees (companies) by patent count
"""

from fastapi import APIRouter, Query
from backend.config import DB_PATH
from backend.db.schema import get_connection

router = APIRouter(prefix="/patents", tags=["patents"])


@router.get("/summary")
def patents_summary():
    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT source, domain_tag, country, COUNT(*) as count FROM patents GROUP BY source, domain_tag, country"
        ).fetchall()

    result: dict = {"total": 0, "by_source": {}, "by_domain": {}, "by_country": {}}
    for row in rows:
        result["total"] += row["count"]
        result["by_source"].setdefault(row["source"], 0)
        result["by_source"][row["source"]] += row["count"]
        result["by_domain"].setdefault(row["domain_tag"], 0)
        result["by_domain"][row["domain_tag"]] += row["count"]
        result["by_country"].setdefault(row["country"], 0)
        result["by_country"][row["country"]] += row["count"]

    return result


@router.get("/trend")
def patents_trend(domain: str | None = Query(None)):
    """Monthly patent counts by domain (uses publication_date)."""
    where = "WHERE publication_date != '' AND publication_date IS NOT NULL"
    params: list = []
    if domain:
        where += " AND domain_tag = ?"
        params.append(domain)

    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            f"""
            SELECT
                strftime('%Y-%m', publication_date) AS month,
                domain_tag,
                COUNT(*) AS count
            FROM patents
            {where}
            GROUP BY month, domain_tag
            ORDER BY month
            """,
            params,
        ).fetchall()

    months: dict[str, dict] = {}
    for row in rows:
        m = row["month"]
        if not m:
            continue
        months.setdefault(m, {"month": m})
        months[m][row["domain_tag"]] = row["count"]

    return sorted(months.values(), key=lambda x: x["month"])


@router.get("/top-assignees")
def top_assignees(
    domain: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(15, ge=1, le=50),
):
    """Top patent-filing organisations."""
    where_clauses = ["assignee != ''", "assignee IS NOT NULL"]
    params: list = []
    if domain:
        where_clauses.append("domain_tag = ?")
        params.append(domain)
    if source:
        where_clauses.append("source = ?")
        params.append(source)

    where = "WHERE " + " AND ".join(where_clauses)

    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            f"""
            SELECT assignee, domain_tag, COUNT(*) as count
            FROM patents
            {where}
            GROUP BY assignee, domain_tag
            ORDER BY count DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()

    return [dict(r) for r in rows]


@router.get("/list")
def list_patents(
    domain: str | None = Query(None),
    source: str | None = Query(None),
    country: str | None = Query(None),
    q: str | None = Query(None, description="Search title/abstract"),
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
    if country:
        where_clauses.append("country = ?")
        params.append(country)
    if q:
        where_clauses.append("(title LIKE ? OR abstract LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    offset = (page - 1) * page_size

    with get_connection(DB_PATH) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM patents {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT patent_number, title, inventors, assignee,
                   filing_date, publication_date, ipc_codes,
                   source, country, domain_tag
            FROM patents
            {where}
            ORDER BY publication_date DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": -(-total // page_size),
        "items": [dict(r) for r in rows],
    }

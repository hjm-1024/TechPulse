"""
/api/summary   — counts by source × domain
/api/trend     — monthly paper counts by domain
/api/top       — top-cited papers
/api/sources   — per-source breakdown for bar chart
"""

from fastapi import APIRouter, Query
from backend.config import DB_PATH
from backend.db.schema import get_connection

router = APIRouter(tags=["stats"])


@router.get("/summary")
def summary():
    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT source, domain_tag, COUNT(*) as count FROM papers GROUP BY source, domain_tag"
        ).fetchall()

    result: dict = {"total": 0, "by_source": {}, "by_domain": {}}
    for row in rows:
        src, domain, count = row["source"], row["domain_tag"], row["count"]
        result["total"] += count
        result["by_source"].setdefault(src, 0)
        result["by_source"][src] += count
        result["by_domain"].setdefault(domain, 0)
        result["by_domain"][domain] += count

    return result


@router.get("/trend")
def trend(domain: str | None = Query(None, description="Filter by domain_tag")):
    """Monthly paper counts. Returns [{month, physical_ai_robotics, telecom_6g}]."""
    where = "WHERE published_date != '' AND published_date IS NOT NULL"
    params: list = []
    if domain:
        where += " AND domain_tag = ?"
        params.append(domain)

    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            f"""
            SELECT
                strftime('%Y-%m', published_date) AS month,
                domain_tag,
                COUNT(*) AS count
            FROM papers
            {where}
            GROUP BY month, domain_tag
            ORDER BY month
            """,
            params,
        ).fetchall()

    # Pivot into [{month, physical_ai_robotics, telecom_6g}]
    months: dict[str, dict] = {}
    for row in rows:
        m = row["month"]
        if m is None:
            continue
        months.setdefault(m, {"month": m})
        months[m][row["domain_tag"]] = row["count"]

    return sorted(months.values(), key=lambda x: x["month"])


@router.get("/top")
def top_papers(
    domain: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    where_clauses = ["citation_count > 0"]
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
            SELECT title, authors, published_date, source, doi,
                   citation_count, journal, domain_tag
            FROM papers
            {where}
            ORDER BY citation_count DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()

    return [dict(r) for r in rows]


@router.get("/sources")
def sources_breakdown():
    """Per-source counts for each domain — used for grouped bar chart."""
    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT source, domain_tag, COUNT(*) as count
            FROM papers
            GROUP BY source, domain_tag
            ORDER BY source
            """
        ).fetchall()
    return [dict(r) for r in rows]

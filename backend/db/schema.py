import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from backend.utils.logger import get_logger

logger = get_logger(__name__)

CREATE_PAPERS_TABLE = """
CREATE TABLE IF NOT EXISTS papers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    abstract        TEXT,
    authors         TEXT,
    published_date  TEXT,
    source          TEXT,
    doi             TEXT,
    citation_count  INTEGER DEFAULT 0,
    journal         TEXT,
    domain_tag      TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(doi),
    UNIQUE(title, source)
)
"""

CREATE_IDX_DOI = "CREATE INDEX IF NOT EXISTS idx_doi ON papers(doi)"
CREATE_IDX_DOMAIN = "CREATE INDEX IF NOT EXISTS idx_domain ON papers(domain_tag)"
CREATE_IDX_DATE = "CREATE INDEX IF NOT EXISTS idx_date ON papers(published_date)"


@contextmanager
def get_connection(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate_add_embeddings(db_path: str) -> None:
    """Safe migration: add embedding BLOB column to papers and patents if missing."""
    with get_connection(db_path) as conn:
        for table in ("papers", "patents"):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN embedding BLOB")
                logger.info("Migration: added embedding column to %s", table)
            except Exception:
                pass  # column already exists


def init_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(CREATE_PAPERS_TABLE)
        conn.execute(CREATE_IDX_DOI)
        conn.execute(CREATE_IDX_DOMAIN)
        conn.execute(CREATE_IDX_DATE)

    logger.info("Database initialised at %s", db_path)


def _normalize_title(title: str) -> str:
    """소문자 변환 + 특수문자 제거 → 중복 감지용 정규화 키."""
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def upsert_papers(db_path: str, papers: list[dict]) -> tuple[int, int, int]:
    """Insert or update papers. Returns (inserted, updated, skipped).
    On duplicate: if new citation_count is higher, UPDATE; otherwise skip.
    """
    inserted = updated = skipped = 0
    with get_connection(db_path) as conn:
        for p in papers:
            try:
                conn.execute(
                    """
                    INSERT INTO papers
                        (title, abstract, authors, published_date, source,
                         doi, citation_count, journal, domain_tag)
                    VALUES
                        (:title, :abstract, :authors, :published_date, :source,
                         :doi, :citation_count, :journal, :domain_tag)
                    """,
                    p,
                )
                inserted += 1
            except sqlite3.IntegrityError:
                existing = conn.execute(
                    "SELECT citation_count FROM papers WHERE doi=? OR (title=? AND source=?)",
                    (p.get("doi"), p.get("title"), p.get("source")),
                ).fetchone()
                if existing and (p.get("citation_count") or 0) > (existing["citation_count"] or 0):
                    conn.execute(
                        "UPDATE papers SET citation_count=?, abstract=? WHERE doi=? OR (title=? AND source=?)",
                        (p.get("citation_count"), p.get("abstract"), p.get("doi"), p.get("title"), p.get("source")),
                    )
                    updated += 1
                else:
                    skipped += 1

    return inserted, updated, skipped


def dedup_papers(db_path: str, dry_run: bool = False) -> tuple[int, int]:
    """Cross-source deduplication by normalized title.
    Keeps the record with highest citation_count (or DOI present).
    Returns (duplicate_groups_found, records_removed).
    """
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT id, title, doi, citation_count FROM papers").fetchall()

    groups: dict[str, list] = {}
    for row in rows:
        key = _normalize_title(row["title"])
        groups.setdefault(key, []).append(dict(row))

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    removed = 0

    with get_connection(db_path) as conn:
        for key, records in dup_groups.items():
            # Sort: DOI present first, then by citation_count desc
            records.sort(key=lambda r: (r["doi"] is not None, r["citation_count"] or 0), reverse=True)
            keep = records[0]
            # Update keeper's citation_count to group max
            max_citations = max(r["citation_count"] or 0 for r in records)
            if not dry_run:
                conn.execute("UPDATE papers SET citation_count=? WHERE id=?", (max_citations, keep["id"]))
            for dup in records[1:]:
                logger.info("dedup: removing id=%d title=%s", dup["id"], dup["title"][:60])
                if not dry_run:
                    conn.execute("DELETE FROM papers WHERE id=?", (dup["id"],))
                removed += 1

    logger.info("dedup: %d duplicate groups, %d records %s",
                len(dup_groups), removed, "would be removed (dry-run)" if dry_run else "removed")
    return len(dup_groups), removed

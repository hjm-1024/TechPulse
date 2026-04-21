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


def upsert_papers(db_path: str, papers: list[dict]) -> tuple[int, int]:
    """Insert papers; skip duplicates. Returns (inserted, skipped)."""
    inserted = skipped = 0
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
                skipped += 1

    return inserted, skipped

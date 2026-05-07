import sqlite3
from backend.db.schema import get_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)

CREATE_PATENTS_TABLE = """
CREATE TABLE IF NOT EXISTS patents (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    patent_number    TEXT NOT NULL,
    title            TEXT NOT NULL,
    abstract         TEXT,
    inventors        TEXT,
    assignee         TEXT,
    filing_date      TEXT,
    publication_date TEXT,
    ipc_codes        TEXT,
    source           TEXT,
    country          TEXT DEFAULT 'US',
    domain_tag       TEXT,
    quality_flag     TEXT,
    cleaned_at       TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    UNIQUE(patent_number, source)
)
"""

CREATE_IDX_PATENT_DOMAIN = "CREATE INDEX IF NOT EXISTS idx_patent_domain ON patents(domain_tag)"
CREATE_IDX_PATENT_DATE   = "CREATE INDEX IF NOT EXISTS idx_patent_date   ON patents(publication_date)"
CREATE_IDX_PATENT_SRC    = "CREATE INDEX IF NOT EXISTS idx_patent_src    ON patents(source)"


def init_patents_db(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(CREATE_PATENTS_TABLE)
        conn.execute(CREATE_IDX_PATENT_DOMAIN)
        conn.execute(CREATE_IDX_PATENT_DATE)
        conn.execute(CREATE_IDX_PATENT_SRC)
    logger.info("Patents table initialised at %s", db_path)


def update_patent_parties(db_path: str, patent_number: str, source: str,
                          assignee: str, inventors: str) -> bool:
    """Update assignee/inventors for one patent. Returns True if a row was changed."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "UPDATE patents SET assignee=?, inventors=? WHERE patent_number=? AND source=?",
            (assignee, inventors, patent_number, source),
        )
        return cur.rowcount > 0


_INSERT_PATENT_SQL = """
    INSERT INTO patents
        (patent_number, title, abstract, inventors, assignee,
         filing_date, publication_date, ipc_codes,
         source, country, domain_tag,
         quality_flag, cleaned_at)
    VALUES
        (:patent_number, :title, :abstract, :inventors, :assignee,
         :filing_date, :publication_date, :ipc_codes,
         :source, :country, :domain_tag,
         :quality_flag, datetime('now'))
"""


def upsert_patents(db_path: str, patents: list[dict]) -> tuple[int, int]:
    """Clean and insert patents, skip duplicates. Returns (inserted, skipped).

    Applies text cleaning (clean_title/clean_abstract) and flags short abstracts
    with quality_flag='short_abstract' so they are excluded from analysis.
    """
    from backend.utils.text_cleaner import clean_title, clean_abstract, is_valid_abstract

    inserted = skipped = 0
    with get_connection(db_path) as conn:
        for raw in patents:
            p = dict(raw)
            p["title"]    = clean_title(p.get("title", ""))
            p["abstract"] = clean_abstract(p.get("abstract", ""))
            if not p["title"]:
                skipped += 1
                continue
            if not is_valid_abstract(p["abstract"]):
                p["quality_flag"] = "short_abstract"
            else:
                p.setdefault("quality_flag", None)
            try:
                conn.execute(_INSERT_PATENT_SQL, p)
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return inserted, skipped

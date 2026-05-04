"""
Schema additions for v1.3 data-quality work.

Idempotent: safe to call any number of times.
- Adds quality_flag, cleaned_at columns to papers/patents (if missing)
- Creates paper_domains, patent_domains, domain_prototypes tables
"""

from backend.db.schema import get_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)


_NEW_COLUMNS = [
    ("papers",  "quality_flag", "TEXT"),
    ("papers",  "cleaned_at",   "TEXT"),
    ("patents", "quality_flag", "TEXT"),
    ("patents", "cleaned_at",   "TEXT"),
]

_PAPER_DOMAINS_SQL = """
CREATE TABLE IF NOT EXISTS paper_domains (
    paper_id   INTEGER NOT NULL,
    domain_tag TEXT    NOT NULL,
    score      REAL    NOT NULL,
    rank       INTEGER NOT NULL,
    PRIMARY KEY (paper_id, domain_tag),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
)
"""

_PATENT_DOMAINS_SQL = """
CREATE TABLE IF NOT EXISTS patent_domains (
    patent_id  INTEGER NOT NULL,
    domain_tag TEXT    NOT NULL,
    score      REAL    NOT NULL,
    rank       INTEGER NOT NULL,
    PRIMARY KEY (patent_id, domain_tag),
    FOREIGN KEY (patent_id) REFERENCES patents(id) ON DELETE CASCADE
)
"""

_DOMAIN_PROTOTYPES_SQL = """
CREATE TABLE IF NOT EXISTS domain_prototypes (
    domain_tag TEXT PRIMARY KEY,
    embedding  BLOB NOT NULL,
    seed_text  TEXT NOT NULL,
    built_at   TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_paper_domains_tag   ON paper_domains(domain_tag, score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_patent_domains_tag  ON patent_domains(domain_tag, score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_papers_quality      ON papers(quality_flag)",
    "CREATE INDEX IF NOT EXISTS idx_patents_quality     ON patents(quality_flag)",
]


def _add_column_if_missing(conn, table: str, column: str, ddl_type: str) -> bool:
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column in cols:
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
    logger.info("schema: %s.%s added", table, column)
    return True


def migrate_quality_schema(db_path: str, dry_run: bool = False) -> dict:
    """
    Add v1.3 schema elements. Returns a summary dict of what changed.
    """
    summary = {"columns_added": [], "tables_created": []}

    with get_connection(db_path) as conn:
        existing_tables = {
            r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }

        for table in ("papers", "patents"):
            if table not in existing_tables:
                logger.warning("schema: table %s missing — run init_db / init_patents_db first", table)

        for table, col, ddl in _NEW_COLUMNS:
            if table not in existing_tables:
                continue
            cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            if col in cols:
                continue
            if dry_run:
                logger.info("schema [dry-run]: would add %s.%s", table, col)
                summary["columns_added"].append(f"{table}.{col}")
            else:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                logger.info("schema: %s.%s added", table, col)
                summary["columns_added"].append(f"{table}.{col}")

        for sql, name in (
            (_PAPER_DOMAINS_SQL,     "paper_domains"),
            (_PATENT_DOMAINS_SQL,    "patent_domains"),
            (_DOMAIN_PROTOTYPES_SQL, "domain_prototypes"),
        ):
            if name in existing_tables:
                continue
            if dry_run:
                logger.info("schema [dry-run]: would create table %s", name)
                summary["tables_created"].append(name)
            else:
                conn.execute(sql)
                logger.info("schema: created table %s", name)
                summary["tables_created"].append(name)

        if not dry_run:
            for ddl in _INDEXES:
                conn.execute(ddl)

    return summary

"""collection_config table — stores keywords, domains, source settings."""
import sqlite3
from backend.db.schema import get_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)

CREATE_CONFIG_TABLE = """
CREATE TABLE IF NOT EXISTS collection_config (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT NOT NULL UNIQUE,
    domain_tag      TEXT NOT NULL,
    active          INTEGER DEFAULT 1,
    sources         TEXT DEFAULT 'arxiv,semantic_scholar,openalex,epo',
    days_back       INTEGER DEFAULT 365,
    added_at        TEXT DEFAULT (datetime('now')),
    last_collected  TEXT
)
"""

# Default config matching current hardcoded values
_DEFAULT_KEYWORDS = [
    # Physical AI & Robotics
    ("physical AI",       "physical_ai_robotics"),
    ("humanoid robot",    "physical_ai_robotics"),
    ("robot learning",    "physical_ai_robotics"),
    ("embodied AI",       "physical_ai_robotics"),
    ("autonomous robot",  "physical_ai_robotics"),
    ("robot manipulation","physical_ai_robotics"),
    # Telecom & 6G
    ("6G",                "telecom_6g"),
    ("mobile communication", "telecom_6g"),
    ("terahertz communication", "telecom_6g"),
    ("massive MIMO",      "telecom_6g"),
    ("network slicing",   "telecom_6g"),
    ("edge computing",    "telecom_6g"),
]


def init_collection_config(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute(CREATE_CONFIG_TABLE)
        # Seed defaults if table is empty
        count = conn.execute("SELECT COUNT(*) FROM collection_config").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO collection_config (keyword, domain_tag) VALUES (?, ?)",
                _DEFAULT_KEYWORDS,
            )
            logger.info("collection_config: seeded %d default keywords", len(_DEFAULT_KEYWORDS))
        else:
            logger.info("collection_config: %d keywords loaded", count)


def get_active_keywords(db_path: str) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM collection_config WHERE active=1 ORDER BY domain_tag, keyword"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_keywords(db_path: str) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM collection_config ORDER BY domain_tag, keyword"
        ).fetchall()
    return [dict(r) for r in rows]

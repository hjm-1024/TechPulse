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

# 미래유망기술 생태계 모니터링 키워드 (도메인별)
_DEFAULT_KEYWORDS = [
    # Physical AI & Robotics
    ("physical AI",            "physical_ai_robotics"),
    ("humanoid robot",         "physical_ai_robotics"),
    ("robot learning",         "physical_ai_robotics"),
    ("embodied AI",            "physical_ai_robotics"),
    ("autonomous robot",       "physical_ai_robotics"),
    ("robot manipulation",     "physical_ai_robotics"),
    ("dexterous hand",         "physical_ai_robotics"),
    ("legged robot",           "physical_ai_robotics"),
    # Generative AI & LLM
    ("large language model",   "generative_ai"),
    ("foundation model",       "generative_ai"),
    ("generative AI",          "generative_ai"),
    ("AI agent",               "generative_ai"),
    ("multimodal model",       "generative_ai"),
    ("retrieval augmented generation", "generative_ai"),
    ("AI alignment",           "generative_ai"),
    # Telecom & 6G
    ("6G",                     "telecom_6g"),
    ("terahertz communication","telecom_6g"),
    ("massive MIMO",           "telecom_6g"),
    ("network slicing",        "telecom_6g"),
    ("edge computing",         "telecom_6g"),
    ("reconfigurable intelligent surface", "telecom_6g"),
    # Biotechnology & Life Science
    ("CRISPR",                 "biotech_life_science"),
    ("gene editing",           "biotech_life_science"),
    ("synthetic biology",      "biotech_life_science"),
    ("mRNA therapeutics",      "biotech_life_science"),
    ("protein folding",        "biotech_life_science"),
    ("cell therapy",           "biotech_life_science"),
    ("drug discovery AI",      "biotech_life_science"),
    ("longevity",              "biotech_life_science"),
    # Quantum Computing
    ("quantum computing",      "quantum"),
    ("quantum error correction","quantum"),
    ("quantum algorithm",      "quantum"),
    ("quantum cryptography",   "quantum"),
    ("topological qubit",      "quantum"),
    ("post-quantum cryptography", "quantum"),
    # Semiconductors & Hardware
    ("2nm chip",               "semiconductors"),
    ("gate-all-around",        "semiconductors"),
    ("chiplet",                "semiconductors"),
    ("neuromorphic computing", "semiconductors"),
    ("photonic chip",          "semiconductors"),
    ("high bandwidth memory",  "semiconductors"),
    ("advanced packaging",     "semiconductors"),
    # Clean Energy
    ("nuclear fusion",         "clean_energy"),
    ("solid state battery",    "clean_energy"),
    ("green hydrogen",         "clean_energy"),
    ("perovskite solar cell",  "clean_energy"),
    ("carbon capture",         "clean_energy"),
    ("small modular reactor",  "clean_energy"),
    # Space Technology
    ("reusable rocket",        "space_tech"),
    ("satellite internet",     "space_tech"),
    ("in-space manufacturing", "space_tech"),
    ("asteroid mining",        "space_tech"),
    ("lunar economy",          "space_tech"),
    # Brain-Computer Interface
    ("brain-computer interface", "bci_neurotech"),
    ("neural implant",         "bci_neurotech"),
    ("electrocorticography",   "bci_neurotech"),
    ("neural decoding",        "bci_neurotech"),
    # Climate Tech
    ("direct air capture",     "climate_tech"),
    ("cultivated meat",        "climate_tech"),
    ("sustainable aviation fuel", "climate_tech"),
    ("circular economy",       "climate_tech"),
    ("precision fermentation", "climate_tech"),
]

# 도메인별 메타데이터 (UI 표시용)
DOMAIN_META: dict[str, dict] = {
    "physical_ai_robotics": {"label": "Physical AI & Robotics", "label_ko": "물리AI/로봇", "color": "#10b981"},
    "generative_ai":        {"label": "Generative AI & LLM",    "label_ko": "생성AI/LLM",  "color": "#6366f1"},
    "telecom_6g":           {"label": "Telecom & 6G",           "label_ko": "통신/6G",     "color": "#f59e0b"},
    "biotech_life_science": {"label": "Biotech & Life Science", "label_ko": "바이오/생명과학", "color": "#22c55e"},
    "quantum":              {"label": "Quantum Computing",      "label_ko": "양자컴퓨팅",   "color": "#8b5cf6"},
    "semiconductors":       {"label": "Semiconductors",        "label_ko": "반도체",        "color": "#ef4444"},
    "clean_energy":         {"label": "Clean Energy",          "label_ko": "청정에너지",    "color": "#fbbf24"},
    "space_tech":           {"label": "Space Technology",      "label_ko": "우주기술",      "color": "#0ea5e9"},
    "bci_neurotech":        {"label": "BCI & Neurotech",       "label_ko": "뇌-컴인터페이스", "color": "#ec4899"},
    "climate_tech":         {"label": "Climate Tech",          "label_ko": "기후테크",      "color": "#06b6d4"},
}


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


def get_keywords_by_domain(db_path: str) -> dict:
    """키워드를 domain_tag 기준으로 그룹화하여 반환. UI의 도메인 뷰 전용."""
    rows = get_all_keywords(db_path)
    grouped: dict[str, dict] = {}
    for row in rows:
        tag = row["domain_tag"]
        if tag not in grouped:
            meta = DOMAIN_META.get(tag, {"label": tag, "label_ko": tag, "color": "#64748b"})
            grouped[tag] = {**meta, "domain_tag": tag, "keywords": []}
        grouped[tag]["keywords"].append(row)
    return grouped

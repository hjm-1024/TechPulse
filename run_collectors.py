"""
Entry point: run enabled collectors and persist results to SQLite.

Usage:
    python run_collectors.py                          # all sources, 90 days back
    python run_collectors.py --days 30                # custom lookback
    python run_collectors.py --source arxiv           # single source
    python run_collectors.py --source semantic_scholar
    python run_collectors.py --source openalex
    python run_collectors.py --source all             # explicit all (default)
"""

import argparse

from backend.config import DB_PATH, KEYWORDS
from backend.db.schema import init_db, upsert_papers
from backend.collectors.arxiv_collector import fetch_papers as arxiv_fetch
from backend.collectors.semantic_scholar_collector import fetch_papers as ss_fetch
from backend.collectors.openalex_collector import fetch_papers as openalex_fetch
from backend.utils.logger import get_logger

logger = get_logger("run_collectors")

_SOURCES = {
    "arxiv": arxiv_fetch,
    "semantic_scholar": ss_fetch,
    "openalex": openalex_fetch,
}


def _run_source(name: str, fetch_fn, days_back: int) -> None:
    logger.info("=== Starting %s collection (days_back=%d) ===", name, days_back)
    try:
        papers = list(fetch_fn(keywords=KEYWORDS, days_back=days_back))
        inserted, skipped = upsert_papers(DB_PATH, papers)
        logger.info("%s done | inserted=%d skipped=%d", name, inserted, skipped)
    except Exception as exc:
        logger.error("%s collection failed: %s", name, exc, exc_info=True)


def run(source: str = "all", days_back: int = 90) -> None:
    init_db(DB_PATH)

    targets = _SOURCES if source == "all" else {source: _SOURCES[source]}

    for name, fetch_fn in targets.items():
        _run_source(name, fetch_fn, days_back)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TechPulse data collector")
    parser.add_argument(
        "--source",
        choices=[*_SOURCES.keys(), "all"],
        default="all",
        help="Which collector to run (default: all)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Days of history to fetch (default: 90)",
    )
    args = parser.parse_args()
    run(source=args.source, days_back=args.days)

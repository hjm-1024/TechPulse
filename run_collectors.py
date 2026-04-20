"""
Entry point: run all enabled collectors and persist results to SQLite.

Usage:
    python run_collectors.py              # run once immediately
    python run_collectors.py --days 30    # look back 30 days (default 90)
"""

import argparse

from backend.config import DB_PATH, KEYWORDS
from backend.db.schema import init_db, upsert_papers
from backend.collectors.arxiv_collector import fetch_papers as arxiv_fetch
from backend.utils.logger import get_logger

logger = get_logger("run_collectors")


def run(days_back: int = 90) -> None:
    init_db(DB_PATH)

    # --- arXiv ---
    logger.info("Starting arXiv collection (days_back=%d)", days_back)
    papers = list(arxiv_fetch(keywords=KEYWORDS, days_back=days_back))
    inserted, skipped = upsert_papers(DB_PATH, papers)
    logger.info("arXiv done | inserted=%d skipped=%d", inserted, skipped)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TechPulse data collector")
    parser.add_argument("--days", type=int, default=90, help="Days of history to fetch")
    args = parser.parse_args()
    run(days_back=args.days)

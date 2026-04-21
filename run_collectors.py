"""
Entry point: run enabled collectors and persist results to SQLite.

Usage:
    python run_collectors.py                                    # all papers, 90 days
    python run_collectors.py --type papers --source arxiv
    python run_collectors.py --type patents                     # all patent sources
    python run_collectors.py --type patents --source epo --days 1825
    python run_collectors.py --type all                         # papers + patents
"""

import argparse

from backend.config import DB_PATH, KEYWORDS
from backend.db.schema import init_db, upsert_papers
from backend.db.patents_schema import init_patents_db, upsert_patents
from backend.collectors.arxiv_collector import fetch_papers as arxiv_fetch
from backend.collectors.semantic_scholar_collector import fetch_papers as ss_fetch
from backend.collectors.openalex_collector import fetch_papers as openalex_fetch
from backend.collectors.lens_collector import fetch_patents as lens_fetch
from backend.collectors.epo_collector import fetch_patents as epo_fetch, enrich_epo_patents
from backend.db.schema import migrate_add_embeddings
from backend.collectors.kipris_collector import fetch_patents as kipris_fetch
from backend.utils.logger import get_logger

logger = get_logger("run_collectors")

_PAPER_SOURCES = {
    "arxiv": arxiv_fetch,
    "semantic_scholar": ss_fetch,
    "openalex": openalex_fetch,
}

_PATENT_SOURCES = {
    "lens": lens_fetch,      # Lens.org worldwide (free key from lens.org — easiest)
    "epo": epo_fetch,        # EPO OPS worldwide (free key from developers.epo.org)
    "kipris": kipris_fetch,  # Korean patents (free key from data.go.kr)
}


def _run_papers(source: str, days_back: int) -> None:
    targets = _PAPER_SOURCES if source == "all" else {source: _PAPER_SOURCES[source]}
    for name, fetch_fn in targets.items():
        logger.info("=== Papers: %s (days_back=%d) ===", name, days_back)
        try:
            papers = list(fetch_fn(keywords=KEYWORDS, days_back=days_back))
            inserted, skipped = upsert_papers(DB_PATH, papers)
            logger.info("%s done | inserted=%d skipped=%d", name, inserted, skipped)
        except Exception as exc:
            logger.error("%s failed: %s", name, exc, exc_info=True)


def _run_patents(source: str, days_back: int) -> None:
    targets = _PATENT_SOURCES if source == "all" else {source: _PATENT_SOURCES[source]}
    for name, fetch_fn in targets.items():
        logger.info("=== Patents: %s (days_back=%d) ===", name, days_back)
        try:
            patents = list(fetch_fn(keywords=KEYWORDS, days_back=days_back))
            inserted, skipped = upsert_patents(DB_PATH, patents)
            logger.info("%s done | inserted=%d skipped=%d", name, inserted, skipped)
        except Exception as exc:
            logger.error("%s failed: %s", name, exc, exc_info=True)


def _run_embed() -> None:
    from backend.utils.embeddings import embed_record, embed_text
    from backend.db.schema import get_connection

    # Quick check Ollama is up
    if embed_text("test") is None:
        logger.error("Ollama not reachable at localhost:11434 — is it running?")
        return

    for table, id_col in (("papers", "id"), ("patents", "id")):
        with get_connection(DB_PATH) as conn:
            rows = conn.execute(
                f"SELECT id, title, abstract FROM {table} WHERE embedding IS NULL"
            ).fetchall()

        if not rows:
            logger.info("embed: %s — nothing to do", table)
            continue

        logger.info("embed: %s — %d records to embed", table, len(rows))
        done = 0
        for row in rows:
            vec = embed_record(row["title"], row["abstract"] or "")
            if vec is not None:
                with get_connection(DB_PATH) as conn:
                    conn.execute(
                        f"UPDATE {table} SET embedding=? WHERE id=?",
                        (vec.tobytes(), row["id"]),
                    )
                done += 1
                if done % 100 == 0:
                    logger.info("embed: %s — %d / %d done", table, done, len(rows))

        logger.info("embed: %s — finished %d / %d", table, done, len(rows))


def run(data_type: str, source: str, days_back: int, enrich: bool = False,
        embed: bool = False) -> None:
    init_db(DB_PATH)
    init_patents_db(DB_PATH)
    migrate_add_embeddings(DB_PATH)

    if enrich:
        logger.info("=== EPO party enrichment ===")
        enrich_epo_patents(DB_PATH)
        return

    if embed:
        logger.info("=== Embedding generation ===")
        _run_embed()
        return

    if data_type in ("papers", "all"):
        paper_source = source if source in _PAPER_SOURCES else "all"
        _run_papers(paper_source, days_back)

    if data_type in ("patents", "all"):
        patent_source = source if source in _PATENT_SOURCES else "all"
        _run_patents(patent_source, days_back)


if __name__ == "__main__":
    all_sources = [*_PAPER_SOURCES.keys(), *_PATENT_SOURCES.keys(), "all"]

    parser = argparse.ArgumentParser(description="TechPulse data collector")
    parser.add_argument(
        "--type",
        choices=["papers", "patents", "all"],
        default="papers",
        help="Data type to collect (default: papers)",
    )
    parser.add_argument(
        "--source",
        choices=all_sources,
        default="all",
        help="Specific source to run (default: all)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Days of history to fetch (default: 90)",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Fill in missing EPO assignee/inventor data via individual patent lookups",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate nomic-embed-text embeddings for all papers/patents (requires Ollama)",
    )
    args = parser.parse_args()
    run(data_type=args.type, source=args.source, days_back=args.days,
        enrich=args.enrich, embed=args.embed)

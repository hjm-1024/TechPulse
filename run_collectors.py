"""
Entry point: run enabled collectors and persist results to SQLite.

Keywords and domain tags are loaded from the collection_config DB table.
All data is collected from 2020-01-01 onwards (days_back per keyword in DB).

Usage:
    python run_collectors.py                                      # all papers
    python run_collectors.py --type patents --source epo          # EPO only
    python run_collectors.py --type patents --domain quantum       # one domain
    python run_collectors.py --type all                           # papers + patents
    python run_collectors.py --type all --reset                   # wipe DB first

Available domains:
    physical_ai_robotics  generative_ai  telecom_6g  biotech_life_science
    quantum  semiconductors  clean_energy  space_tech  bci_neurotech
    advanced_materials  web3_blockchain  climate_tech  low_carbon
"""

import argparse
from datetime import datetime, timezone

from backend.config import DB_PATH
from backend.db.schema import init_db, upsert_papers, dedup_papers
from backend.db.patents_schema import init_patents_db, upsert_patents
from backend.db.config_schema import init_collection_config, get_active_keywords
from backend.collectors.arxiv_collector import fetch_papers as arxiv_fetch
from backend.collectors.semantic_scholar_collector import fetch_papers as ss_fetch
from backend.collectors.openalex_collector import fetch_papers as openalex_fetch
from backend.collectors.lens_collector import fetch_patents as lens_fetch
from backend.collectors.epo_collector import fetch_patents as epo_fetch, enrich_epo_patents
from backend.db.schema import migrate_add_embeddings
from backend.collectors.kipris_collector import fetch_patents as kipris_fetch
from backend.utils.logger import get_logger

logger = get_logger("run_collectors")


def _load_keywords_from_db(domain: str | None = None) -> tuple[list[str], dict[str, str]]:
    """DB collection_config에서 활성 키워드와 domain_tag_map 로드. domain 지정 시 해당 도메인만."""
    rows = get_active_keywords(DB_PATH)
    if not rows:
        logger.warning("collection_config가 비어 있습니다. 기본값으로 시드합니다.")
        init_collection_config(DB_PATH)
        rows = get_active_keywords(DB_PATH)
    if domain:
        rows = [r for r in rows if r["domain_tag"] == domain]
        if not rows:
            raise ValueError(f"도메인 '{domain}'에 활성 키워드가 없습니다.")
    keywords = [r["keyword"] for r in rows]
    domain_tag_map = {r["keyword"]: r["domain_tag"] for r in rows}
    domain_str = f"domain={domain}" if domain else f"도메인 {len(set(domain_tag_map.values()))}개"
    logger.info("키워드 %d개 로드 (%s)", len(keywords), domain_str)
    return keywords, domain_tag_map


def _mark_collected(keywords: list[str]) -> None:
    """수집 완료된 키워드의 last_collected 타임스탬프 업데이트."""
    from backend.db.schema import get_connection
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_connection(DB_PATH) as conn:
        for kw in keywords:
            conn.execute(
                "UPDATE collection_config SET last_collected=? WHERE keyword=?",
                (now, kw),
            )

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


def _run_papers(source: str, days_back: int, domain: str | None = None) -> None:
    keywords, domain_tag_map = _load_keywords_from_db(domain)
    targets = _PAPER_SOURCES if source == "all" else {source: _PAPER_SOURCES[source]}
    for name, fetch_fn in targets.items():
        logger.info("=== Papers: %s (days_back=%d, keywords=%d) ===", name, days_back, len(keywords))
        try:
            papers = list(fetch_fn(keywords=keywords, days_back=days_back, domain_tag_map=domain_tag_map))
            inserted, updated, skipped = upsert_papers(DB_PATH, papers)
            logger.info("%s done | inserted=%d updated=%d skipped=%d", name, inserted, updated, skipped)
            _mark_collected(keywords)
        except Exception as exc:
            logger.error("%s failed: %s", name, exc, exc_info=True)


def _run_patents(source: str, days_back: int, domain: str | None = None) -> None:
    keywords, domain_tag_map = _load_keywords_from_db(domain)
    targets = _PATENT_SOURCES if source == "all" else {source: _PATENT_SOURCES[source]}
    for name, fetch_fn in targets.items():
        logger.info("=== Patents: %s (days_back=%d, keywords=%d) ===", name, days_back, len(keywords))
        try:
            patents = list(fetch_fn(keywords=keywords, days_back=days_back, domain_tag_map=domain_tag_map))
            inserted, skipped = upsert_patents(DB_PATH, patents)
            logger.info("%s done | inserted=%d skipped=%d", name, inserted, skipped)
            _mark_collected(keywords)
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


def _run_clean_names() -> None:
    from backend.db.schema import get_connection
    from backend.utils.text_utils import clean_assignee, clean_inventors
    with get_connection(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT id, assignee, inventors FROM patents WHERE assignee IS NOT NULL OR inventors IS NOT NULL"
        ).fetchall()
    updated = 0
    for row in rows:
        new_a = clean_assignee(row["assignee"] or "")
        new_i = clean_inventors(row["inventors"] or "")
        if new_a != (row["assignee"] or "") or new_i != (row["inventors"] or ""):
            with get_connection(DB_PATH) as conn:
                conn.execute("UPDATE patents SET assignee=?, inventors=? WHERE id=?",
                             (new_a, new_i, row["id"]))
            updated += 1
    logger.info("clean-names: updated %d / %d patent records", updated, len(rows))


def _reset_data() -> None:
    """논문·특허 데이터만 삭제. collection_config(키워드 설정)은 유지."""
    from backend.db.schema import get_connection
    with get_connection(DB_PATH) as conn:
        conn.execute("DELETE FROM papers")
        conn.execute("DELETE FROM patents")
    logger.info("기존 papers/patents 데이터 삭제 완료. 키워드 설정은 유지됨.")


def run(data_type: str, source: str, days_back: int, domain: str | None = None,
        enrich: bool = False, embed: bool = False, clean_names: bool = False,
        reset: bool = False, **kwargs) -> None:
    init_db(DB_PATH)
    init_patents_db(DB_PATH)
    migrate_add_embeddings(DB_PATH)
    init_collection_config(DB_PATH)

    if reset:
        _reset_data()

    if enrich:
        logger.info("=== EPO party enrichment ===")
        enrich_epo_patents(DB_PATH)
        return

    if embed:
        logger.info("=== Embedding generation ===")
        _run_embed()
        return

    if clean_names:
        logger.info("=== Cleaning party names ===")
        _run_clean_names()
        return

    if kwargs.get("dedup"):
        dry_run = kwargs.get("dry_run", False)
        logger.info("=== Cross-source deduplication%s ===", " [dry-run]" if dry_run else "")
        groups, removed = dedup_papers(DB_PATH, dry_run=dry_run)
        logger.info("dedup done | duplicate_groups=%d records_removed=%d", groups, removed)
        return

    if data_type in ("papers", "all"):
        paper_source = source if source in _PAPER_SOURCES else "all"
        _run_papers(paper_source, days_back, domain)

    if data_type in ("patents", "all"):
        patent_source = source if source in _PATENT_SOURCES else "all"
        _run_patents(patent_source, days_back, domain)


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
        default=2300,
        help="Days of history to fetch (default: 2300 ≈ from 2020-01-01)",
    )
    parser.add_argument(
        "--domain",
        default=None,
        metavar="DOMAIN_TAG",
        help=(
            "Collect only this domain (e.g. quantum, semiconductors). "
            "Useful for staying under EPO 4GB/week bandwidth limit. "
            "Run one domain at a time and resume after limit resets."
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing papers/patents before collecting (keyword config is preserved)",
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
    parser.add_argument(
        "--clean-names",
        action="store_true",
        dest="clean_names",
        help="Remove EPO [XX] country suffixes from assignee/inventor names in DB",
    )
    parser.add_argument(
        "--dedup",
        action="store_true",
        help="Find and remove cross-source duplicate papers by normalized title",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="With --dedup: log what would be removed without deleting anything",
    )
    args = parser.parse_args()
    run(data_type=args.type, source=args.source, days_back=args.days,
        domain=args.domain, enrich=args.enrich, embed=args.embed,
        clean_names=args.clean_names, dedup=args.dedup, dry_run=args.dry_run,
        reset=args.reset)

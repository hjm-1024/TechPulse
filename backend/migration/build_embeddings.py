"""
Generate Ollama embeddings for rows where embedding IS NULL.

Idempotent: only NULL embeddings are computed.
Skips rows flagged as 'short_abstract' or 'duplicate' (won't enter analysis anyway).
"""

from backend.db.schema import get_connection
from backend.utils.embeddings import embed_record, embed_text
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _ollama_alive() -> bool:
    return embed_text("ping") is not None


def build_embeddings(db_path: str, table: str, dry_run: bool = False,
                     batch_size: int = 100) -> dict:
    summary = {"table": table, "scanned": 0, "embedded": 0, "failed": 0}

    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""SELECT id, title, abstract FROM {table}
                WHERE embedding IS NULL
                  AND (quality_flag IS NULL OR quality_flag NOT IN ('short_abstract','duplicate'))"""
        ).fetchall()

    summary["scanned"] = len(rows)
    if not rows:
        logger.info("embed: %s — nothing to embed", table)
        return summary

    if dry_run:
        logger.info("embed [dry-run]: %s — would embed %d rows", table, len(rows))
        summary["embedded"] = len(rows)
        return summary

    if not _ollama_alive():
        logger.error("embed: Ollama not reachable; aborting %s", table)
        summary["failed"] = len(rows)
        return summary

    pending: list[tuple[bytes, int]] = []
    for i, row in enumerate(rows, 1):
        vec = embed_record(row["title"] or "", row["abstract"] or "")
        if vec is None:
            summary["failed"] += 1
            continue
        pending.append((vec.tobytes(), row["id"]))

        if len(pending) >= batch_size:
            with get_connection(db_path) as conn:
                conn.executemany(
                    f"UPDATE {table} SET embedding=? WHERE id=?", pending
                )
            summary["embedded"] += len(pending)
            pending.clear()
            logger.info("embed: %s — %d / %d done", table, summary["embedded"], len(rows))

    if pending:
        with get_connection(db_path) as conn:
            conn.executemany(
                f"UPDATE {table} SET embedding=? WHERE id=?", pending
            )
        summary["embedded"] += len(pending)

    logger.info(
        "embed: %s — embedded %d, failed %d (of %d scanned)",
        table, summary["embedded"], summary["failed"], summary["scanned"],
    )
    return summary


def build_all(db_path: str, dry_run: bool = False) -> list[dict]:
    return [
        build_embeddings(db_path, "papers",  dry_run=dry_run),
        build_embeddings(db_path, "patents", dry_run=dry_run),
    ]

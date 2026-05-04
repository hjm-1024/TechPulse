"""
Apply text_cleaner.clean_text() to all rows whose `cleaned_at` is NULL.

Idempotent: rows already cleaned (cleaned_at IS NOT NULL) are skipped.
"""

from backend.db.schema import get_connection
from backend.utils.text_cleaner import clean_text
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def clean_table_texts(db_path: str, table: str, dry_run: bool = False,
                      batch_size: int = 500) -> dict:
    """
    Update title/abstract for all rows where cleaned_at IS NULL.
    Sets cleaned_at = datetime('now') after a successful update.
    """
    summary = {"table": table, "scanned": 0, "updated": 0, "unchanged": 0}

    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT id, title, abstract FROM {table} WHERE cleaned_at IS NULL"
        ).fetchall()

    summary["scanned"] = len(rows)
    if not rows:
        logger.info("clean: %s — nothing to clean", table)
        return summary

    pending: list[tuple[str, str, int]] = []
    for row in rows:
        new_title    = clean_text(row["title"]    or "")
        new_abstract = clean_text(row["abstract"] or "")
        changed = (new_title != (row["title"] or "")) or (new_abstract != (row["abstract"] or ""))
        if changed:
            pending.append((new_title, new_abstract, row["id"]))
        else:
            summary["unchanged"] += 1

    if dry_run:
        logger.info(
            "clean [dry-run]: %s — would update %d rows (unchanged %d)",
            table, len(pending), summary["unchanged"],
        )
        # Even in dry-run, we don't mark cleaned_at — leave for actual run.
        summary["updated"] = len(pending)
        return summary

    # Mark all scanned rows (changed and unchanged) as cleaned to avoid rescan
    with get_connection(db_path) as conn:
        for i in range(0, len(pending), batch_size):
            chunk = pending[i:i + batch_size]
            conn.executemany(
                f"UPDATE {table} SET title=?, abstract=?, "
                f"cleaned_at=datetime('now') WHERE id=?",
                chunk,
            )
            summary["updated"] += len(chunk)

        # Also stamp cleaned_at for rows that were already clean
        all_ids = [row["id"] for row in rows]
        conn.executemany(
            f"UPDATE {table} SET cleaned_at=datetime('now') "
            f"WHERE id=? AND cleaned_at IS NULL",
            [(rid,) for rid in all_ids],
        )

    logger.info(
        "clean: %s — updated %d, unchanged %d (of %d scanned)",
        table, summary["updated"], summary["unchanged"], summary["scanned"],
    )
    return summary


def clean_all(db_path: str, dry_run: bool = False) -> list[dict]:
    return [
        clean_table_texts(db_path, "papers",  dry_run=dry_run),
        clean_table_texts(db_path, "patents", dry_run=dry_run),
    ]

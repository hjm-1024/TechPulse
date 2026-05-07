"""
Mark rows whose abstract fails is_valid_abstract() as quality_flag='short_abstract'.

Idempotent: rows already flagged are not re-touched. Only NULL → 'short_abstract'.
Rows that had a flag for another reason (e.g. 'duplicate') are NOT overwritten.
"""

from backend.db.schema import get_connection
from backend.utils.text_cleaner import is_valid_abstract
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def validate_table(db_path: str, table: str, dry_run: bool = False,
                   min_chars: int = 80) -> dict:
    summary = {"table": table, "scanned": 0, "flagged": 0}

    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT id, abstract FROM {table} WHERE quality_flag IS NULL"
        ).fetchall()

    summary["scanned"] = len(rows)
    to_flag = [
        row["id"] for row in rows
        if not is_valid_abstract(row["abstract"] or "", min_chars=min_chars)
    ]

    if dry_run:
        logger.info(
            "validate [dry-run]: %s — would flag %d / %d rows as short_abstract",
            table, len(to_flag), summary["scanned"],
        )
        summary["flagged"] = len(to_flag)
        return summary

    if to_flag:
        with get_connection(db_path) as conn:
            conn.executemany(
                f"UPDATE {table} SET quality_flag='short_abstract' WHERE id=?",
                [(i,) for i in to_flag],
            )
    summary["flagged"] = len(to_flag)
    logger.info(
        "validate: %s — flagged %d / %d as short_abstract",
        table, summary["flagged"], summary["scanned"],
    )
    return summary


def validate_all(db_path: str, dry_run: bool = False, min_chars: int = 80) -> list[dict]:
    return [
        validate_table(db_path, "papers",  dry_run=dry_run, min_chars=min_chars),
        validate_table(db_path, "patents", dry_run=dry_run, min_chars=min_chars),
    ]

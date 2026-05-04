"""
Hidden duplicate detection via embedding cosine similarity.

For each year bucket, compute pairwise cosine; if a pair >= threshold,
mark the lower-citation row as quality_flag='duplicate' (no deletion).

Idempotent: rows already flagged as 'duplicate' are skipped from candidate set
and not re-flagged. The keeper of each duplicate group is left alone.
"""

import numpy as np

from backend.db.schema import get_connection
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _year(date: str | None) -> str:
    if not date:
        return "unknown"
    return date[:4] if len(date) >= 4 else "unknown"


def dedup_table(db_path: str, table: str, *,
                dry_run: bool = False,
                threshold: float = 0.93) -> dict:
    summary = {
        "table": table, "scanned": 0, "year_buckets": 0,
        "pairs_over_threshold": 0, "newly_flagged": 0,
    }

    date_col = "published_date" if table == "papers" else "publication_date"

    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""SELECT id, {date_col} AS date, citation_count, embedding
                FROM {table}
                WHERE embedding IS NOT NULL
                  AND (quality_flag IS NULL OR quality_flag != 'duplicate')"""
        ).fetchall() if table == "papers" else conn.execute(
            f"""SELECT id, {date_col} AS date, 0 AS citation_count, embedding
                FROM {table}
                WHERE embedding IS NOT NULL
                  AND (quality_flag IS NULL OR quality_flag != 'duplicate')"""
        ).fetchall()

    summary["scanned"] = len(rows)
    if not rows:
        logger.info("dedup-embed: %s — nothing to scan", table)
        return summary

    # Bucket by year
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        y = _year(row["date"])
        buckets.setdefault(y, []).append({
            "id": row["id"],
            "citations": row["citation_count"] or 0,
            "vec": np.frombuffer(row["embedding"], dtype=np.float32),
        })
    summary["year_buckets"] = len(buckets)

    to_flag: set[int] = set()

    for year, items in buckets.items():
        if len(items) < 2:
            continue
        ids   = np.array([it["id"] for it in items])
        cits  = np.array([it["citations"] for it in items])
        mat   = np.stack([it["vec"] for it in items])

        norms = np.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1.0
        normed = mat / norms[:, None]

        # Pairwise cosine via dot product on normalized vectors
        sim = normed @ normed.T
        np.fill_diagonal(sim, -1.0)  # exclude self

        # Find pairs (i, j) with i < j and sim >= threshold
        idx_i, idx_j = np.where(np.triu(sim, k=1) >= threshold)
        summary["pairs_over_threshold"] += len(idx_i)

        for i, j in zip(idx_i.tolist(), idx_j.tolist()):
            # Loser = lower citations; tie → larger id (newer)
            if cits[i] >= cits[j]:
                loser = int(ids[j])
            else:
                loser = int(ids[i])
            to_flag.add(loser)

        if len(idx_i):
            logger.debug(
                "dedup-embed: %s/%s — %d pairs, %d candidates flagged so far",
                table, year, len(idx_i), len(to_flag),
            )

    if dry_run:
        logger.info(
            "dedup-embed [dry-run]: %s — would flag %d rows as duplicate "
            "(scanned %d, %d pairs >= %.2f)",
            table, len(to_flag), summary["scanned"],
            summary["pairs_over_threshold"], threshold,
        )
        summary["newly_flagged"] = len(to_flag)
        return summary

    if to_flag:
        with get_connection(db_path) as conn:
            conn.executemany(
                f"UPDATE {table} SET quality_flag='duplicate' "
                f"WHERE id=? AND quality_flag IS NULL",
                [(i,) for i in to_flag],
            )
    summary["newly_flagged"] = len(to_flag)
    logger.info(
        "dedup-embed: %s — flagged %d new duplicates "
        "(%d pairs >= %.2f, %d year buckets)",
        table, summary["newly_flagged"],
        summary["pairs_over_threshold"], threshold, summary["year_buckets"],
    )
    return summary


def dedup_all(db_path: str, *, dry_run: bool = False,
              threshold: float = 0.93) -> list[dict]:
    return [
        dedup_table(db_path, "papers",  dry_run=dry_run, threshold=threshold),
        dedup_table(db_path, "patents", dry_run=dry_run, threshold=threshold),
    ]

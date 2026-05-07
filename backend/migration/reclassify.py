"""
Multi-label domain reclassification.

For each row with an embedding, compute cosine vs all 13 prototypes,
keep top-K with score >= threshold, write to paper_domains/patent_domains.

Idempotent: replaces all rows for each (paper_id|patent_id) on each run.
Use --since YYYY-MM-DD to only process recent rows.
"""

from datetime import datetime
import numpy as np

from backend.db.schema import get_connection
from backend.migration.build_prototypes import load_prototypes
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _cosine_matrix(query: np.ndarray, prototypes: np.ndarray) -> np.ndarray:
    """query (D,) vs prototypes (K, D) → (K,) cosine similarities."""
    qn = np.linalg.norm(query)
    if qn == 0:
        return np.zeros(prototypes.shape[0], dtype=np.float32)
    pn = np.linalg.norm(prototypes, axis=1)
    pn[pn == 0] = 1.0
    return (prototypes @ query) / (pn * qn)


def reclassify_table(db_path: str, table: str, *,
                     dry_run: bool = False,
                     threshold: float = 0.45,
                     top_k: int = 3,
                     since: str | None = None) -> dict:
    assoc_table = "paper_domains" if table == "papers" else "patent_domains"
    fk_col      = "paper_id"      if table == "papers" else "patent_id"

    protos = load_prototypes(db_path)
    if not protos:
        logger.error("reclassify: no domain_prototypes found — run prototypes step first")
        return {"table": table, "scanned": 0, "labeled": 0, "rows_written": 0}

    tags     = list(protos.keys())
    proto_mx = np.stack([protos[t] for t in tags])

    where = "WHERE embedding IS NOT NULL"
    if since:
        date_col = "published_date" if table == "papers" else "publication_date"
        where += f" AND {date_col} >= '{since}'"

    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT id, embedding FROM {table} {where}"
        ).fetchall()

    summary = {
        "table": table, "scanned": len(rows),
        "labeled": 0, "rows_written": 0,
        "label_count_dist": {1: 0, 2: 0, 3: 0, 0: 0},
        "domain_counts": {t: 0 for t in tags},
    }

    if not rows:
        logger.info("reclassify: %s — nothing to label", table)
        return summary

    # Compute labels in memory first
    labels: list[tuple[int, list[tuple[str, float, int]]]] = []
    for row in rows:
        vec = np.frombuffer(row["embedding"], dtype=np.float32)
        sims = _cosine_matrix(vec, proto_mx)
        order = np.argsort(-sims)[:top_k]
        kept = [(tags[i], float(sims[i])) for i in order if sims[i] >= threshold]
        ranked = [(t, s, rank + 1) for rank, (t, s) in enumerate(kept)]
        labels.append((row["id"], ranked))
        n = len(ranked)
        summary["label_count_dist"][n] = summary["label_count_dist"].get(n, 0) + 1
        for t, _, _ in ranked:
            summary["domain_counts"][t] += 1
        if ranked:
            summary["labeled"] += 1

    if dry_run:
        logger.info(
            "reclassify [dry-run]: %s — would label %d / %d (avg %.2f tags/doc)",
            table, summary["labeled"], summary["scanned"],
            sum(k * v for k, v in summary["label_count_dist"].items()) / max(summary["scanned"], 1),
        )
        logger.info("reclassify [dry-run]: domain dist = %s", summary["domain_counts"])
        return summary

    # Write: replace all rows for each id
    ids = [lid for lid, _ in labels]
    placeholders = ",".join("?" * len(ids))
    with get_connection(db_path) as conn:
        # Delete existing rows for these ids only
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            ph = ",".join("?" * len(chunk))
            conn.execute(
                f"DELETE FROM {assoc_table} WHERE {fk_col} IN ({ph})", chunk
            )
        flat = [
            (lid, tag, score, rank)
            for lid, tags_for_row in labels
            for (tag, score, rank) in tags_for_row
        ]
        if flat:
            conn.executemany(
                f"INSERT INTO {assoc_table} ({fk_col}, domain_tag, score, rank) "
                f"VALUES (?, ?, ?, ?)",
                flat,
            )
        summary["rows_written"] = len(flat)

    logger.info(
        "reclassify: %s — labeled %d / %d, %d assoc rows (avg %.2f tags/doc)",
        table, summary["labeled"], summary["scanned"], summary["rows_written"],
        sum(k * v for k, v in summary["label_count_dist"].items()) / max(summary["scanned"], 1),
    )
    logger.info("reclassify: %s — domain counts: %s", table, summary["domain_counts"])
    return summary


def reclassify_all(db_path: str, *, dry_run: bool = False,
                   threshold: float = 0.45, top_k: int = 3,
                   since: str | None = None) -> list[dict]:
    return [
        reclassify_table(db_path, "papers",  dry_run=dry_run,
                         threshold=threshold, top_k=top_k, since=since),
        reclassify_table(db_path, "patents", dry_run=dry_run,
                         threshold=threshold, top_k=top_k, since=since),
    ]

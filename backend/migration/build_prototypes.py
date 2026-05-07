"""
Build the 13 domain prototype embeddings and cache them in `domain_prototypes`.

Idempotent: if a prototype already exists for a tag, skip unless --rebuild.
"""

import numpy as np

from backend.db.schema import get_connection
from backend.domains import DOMAIN_SEEDS
from backend.utils.embeddings import embed_text
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def build_prototypes(db_path: str, dry_run: bool = False,
                     rebuild: bool = False) -> dict:
    summary = {"built": 0, "skipped": 0, "failed": 0, "tags": []}

    with get_connection(db_path) as conn:
        existing = {
            r["domain_tag"]
            for r in conn.execute("SELECT domain_tag FROM domain_prototypes")
        }

    todo = []
    for tag, entry in DOMAIN_SEEDS.items():
        if tag in existing and not rebuild:
            summary["skipped"] += 1
            continue
        todo.append((tag, entry["seed_text"]))

    if dry_run:
        logger.info(
            "prototypes [dry-run]: would build %d (skip %d existing)",
            len(todo), summary["skipped"],
        )
        summary["built"] = len(todo)
        summary["tags"] = [t for t, _ in todo]
        return summary

    if not todo:
        logger.info("prototypes: all %d domains already built", summary["skipped"])
        return summary

    rows: list[tuple[str, bytes, str]] = []
    for tag, seed in todo:
        vec = embed_text(seed)
        if vec is None:
            logger.error("prototypes: %s — Ollama embed failed", tag)
            summary["failed"] += 1
            continue
        rows.append((tag, vec.astype(np.float32).tobytes(), seed))
        summary["tags"].append(tag)

    with get_connection(db_path) as conn:
        for tag, blob, seed in rows:
            conn.execute(
                """INSERT INTO domain_prototypes (domain_tag, embedding, seed_text)
                   VALUES (?, ?, ?)
                   ON CONFLICT(domain_tag) DO UPDATE SET
                       embedding = excluded.embedding,
                       seed_text = excluded.seed_text,
                       built_at  = datetime('now')""",
                (tag, blob, seed),
            )

    summary["built"] = len(rows)
    logger.info(
        "prototypes: built %d, skipped %d, failed %d",
        summary["built"], summary["skipped"], summary["failed"],
    )
    return summary


def load_prototypes(db_path: str) -> dict[str, np.ndarray]:
    """Load all prototype vectors keyed by domain_tag."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT domain_tag, embedding FROM domain_prototypes"
        ).fetchall()
    return {
        r["domain_tag"]: np.frombuffer(r["embedding"], dtype=np.float32)
        for r in rows
    }

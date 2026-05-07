"""
Migration orchestrator.

Step graph (ordered):
    backup → schema → clean → validate → embed → prototypes → reclassify → dedup

`backup` and `schema` always run first when their step is in the requested set
or when --all is used. They are no-ops on second run.
"""

from typing import Callable

from backend.migration import (
    backup, schema_migrate, clean_texts, validate,
    build_embeddings, build_prototypes, reclassify, dedup_embeddings,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# Canonical step order
STEP_ORDER = [
    "backup", "schema", "clean", "validate",
    "embed", "prototypes", "reclassify", "dedup",
]

# Steps that mutate the DB → require backup beforehand on --all
MUTATING_STEPS = {"clean", "validate", "embed", "prototypes", "reclassify", "dedup"}


def _run_step(name: str, fn: Callable, *args, **kwargs):
    logger.info("──── step: %s ────", name)
    return fn(*args, **kwargs)


def run_migration(
    db_path: str,
    steps: list[str],
    *,
    dry_run: bool = False,
    dup_threshold: float = 0.93,
    reclass_threshold: float = 0.45,
    reclass_top_k: int = 3,
    rebuild_prototypes: bool = False,
    since: str | None = None,
) -> dict:
    """
    Run the requested migration steps in canonical order.

    Returns a summary dict { step_name: result }.
    """
    requested = set(steps)
    invalid = requested - set(STEP_ORDER)
    if invalid:
        raise ValueError(f"Unknown migration steps: {sorted(invalid)}")

    # Auto-prepend backup + schema when any mutating step is requested
    if requested & MUTATING_STEPS:
        requested.add("schema")
        if not dry_run:
            requested.add("backup")

    plan = [s for s in STEP_ORDER if s in requested]
    logger.info("migration plan%s: %s", " [dry-run]" if dry_run else "", plan)

    out: dict = {"plan": plan, "dry_run": dry_run, "results": {}}

    for step in plan:
        if step == "backup":
            out["results"]["backup"] = str(backup.backup_db(db_path, dry_run=dry_run))

        elif step == "schema":
            out["results"]["schema"] = _run_step(
                "schema", schema_migrate.migrate_quality_schema, db_path, dry_run=dry_run,
            )

        elif step == "clean":
            out["results"]["clean"] = _run_step(
                "clean", clean_texts.clean_all, db_path, dry_run=dry_run,
            )

        elif step == "validate":
            out["results"]["validate"] = _run_step(
                "validate", validate.validate_all, db_path, dry_run=dry_run,
            )

        elif step == "embed":
            out["results"]["embed"] = _run_step(
                "embed", build_embeddings.build_all, db_path, dry_run=dry_run,
            )

        elif step == "prototypes":
            out["results"]["prototypes"] = _run_step(
                "prototypes", build_prototypes.build_prototypes,
                db_path, dry_run=dry_run, rebuild=rebuild_prototypes,
            )

        elif step == "reclassify":
            out["results"]["reclassify"] = _run_step(
                "reclassify", reclassify.reclassify_all,
                db_path, dry_run=dry_run,
                threshold=reclass_threshold, top_k=reclass_top_k, since=since,
            )

        elif step == "dedup":
            out["results"]["dedup"] = _run_step(
                "dedup", dedup_embeddings.dedup_all,
                db_path, dry_run=dry_run, threshold=dup_threshold,
            )

    logger.info("migration complete%s", " [dry-run]" if dry_run else "")
    return out

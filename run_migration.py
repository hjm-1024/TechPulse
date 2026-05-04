"""
TechPulse data-quality migration CLI.

Examples:
    # Preview everything (no DB changes, no backup)
    python run_migration.py --dry-run --all

    # Full run (auto backup + all steps in canonical order)
    python run_migration.py --all

    # Just clean & validate existing data
    python run_migration.py --steps clean,validate

    # Build prototypes and reclassify existing data
    python run_migration.py --steps prototypes,reclassify

    # Re-build domain prototypes (overwrites)
    python run_migration.py --steps prototypes --rebuild-prototypes

    # Hidden duplicate detection only (more aggressive threshold)
    python run_migration.py --steps dedup --dup-threshold 0.90

    # Increment-only reclassify (recent data)
    python run_migration.py --steps reclassify --since 2026-04-01

Safety:
    - Mutating steps automatically take a timestamped .bak.YYYYMMDD-HHMMSS.
    - Every step is idempotent (safe to re-run).
    - --dry-run shows what would change without writing anything.
    - Roll back: mv data/techpulse.db.bak.<ts> data/techpulse.db
"""

import argparse
import json
import sys

from backend.config import DB_PATH
from backend.db.schema import init_db, migrate_add_embeddings
from backend.db.patents_schema import init_patents_db
from backend.migration.runner import run_migration, STEP_ORDER
from backend.utils.logger import get_logger

logger = get_logger("run_migration")


def _ensure_base_schema(db_path: str) -> None:
    """Make sure papers/patents tables and embedding column exist."""
    init_db(db_path)
    init_patents_db(db_path)
    migrate_add_embeddings(db_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TechPulse data-quality migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--all", action="store_true",
                        help=f"Run all steps in canonical order: {','.join(STEP_ORDER)}")
    parser.add_argument("--steps", type=str, default="",
                        help="Comma-separated subset of steps")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change without writing")
    parser.add_argument("--dup-threshold", type=float, default=0.93,
                        help="Cosine threshold for hidden-duplicate detection (default: 0.93)")
    parser.add_argument("--reclass-threshold", type=float, default=0.45,
                        help="Min cosine for a domain label to be assigned (default: 0.45)")
    parser.add_argument("--reclass-top-k", type=int, default=3,
                        help="Max domain labels per document (default: 3)")
    parser.add_argument("--rebuild-prototypes", action="store_true",
                        help="Force rebuild of all 13 domain prototype embeddings")
    parser.add_argument("--since", type=str, default=None,
                        help="For reclassify: only process rows with date >= YYYY-MM-DD")
    parser.add_argument("--db", type=str, default=DB_PATH,
                        help=f"DB path (default: {DB_PATH})")
    parser.add_argument("--json", action="store_true",
                        help="Print final summary as JSON")

    args = parser.parse_args()

    if not args.all and not args.steps:
        parser.error("specify --all or --steps")

    if args.all:
        steps = list(STEP_ORDER)
    else:
        steps = [s.strip() for s in args.steps.split(",") if s.strip()]

    _ensure_base_schema(args.db)

    summary = run_migration(
        args.db,
        steps,
        dry_run=args.dry_run,
        dup_threshold=args.dup_threshold,
        reclass_threshold=args.reclass_threshold,
        reclass_top_k=args.reclass_top_k,
        rebuild_prototypes=args.rebuild_prototypes,
        since=args.since,
    )

    if args.json:
        print(json.dumps(summary, indent=2, default=str))
    else:
        logger.info("plan: %s", summary["plan"])
        for step, result in summary["results"].items():
            logger.info("  %-12s → %s", step, result)

    return 0


if __name__ == "__main__":
    sys.exit(main())

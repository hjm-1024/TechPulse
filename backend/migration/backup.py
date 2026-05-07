"""Automatic DB backup before destructive migration steps."""

import shutil
from datetime import datetime
from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger(__name__)


def backup_db(db_path: str, dry_run: bool = False) -> Path:
    """
    Copy the SQLite file to <db_path>.bak.YYYYMMDD-HHMMSS.

    Returns the backup path. In dry-run, returns the would-be path
    without copying.
    """
    src = Path(db_path)
    if not src.exists():
        logger.warning("backup: source DB %s does not exist; nothing to back up", src)
        return src

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = src.with_suffix(src.suffix + f".bak.{ts}")

    if dry_run:
        logger.info("backup [dry-run]: would copy %s → %s", src, dst)
        return dst

    shutil.copy2(src, dst)
    logger.info("backup: copied %s → %s (%.1f MB)", src, dst, dst.stat().st_size / 1e6)
    return dst

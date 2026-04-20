import logging
import os
from pathlib import Path

def get_logger(name: str) -> logging.Logger:
    Path("logs").mkdir(exist_ok=True)

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level, logging.INFO))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler("logs/techpulse.log")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

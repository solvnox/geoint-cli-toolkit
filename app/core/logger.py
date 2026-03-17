"""
Application logging setup.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "geoint_cli", level: int = logging.INFO) -> logging.Logger:
    """Configure and return application logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler - ensure logs dir exists
    try:
        base = Path(__file__).resolve().parent.parent.parent
        log_dir = base / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"geoint_{datetime.now().strftime('%Y%m%d')}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass

    return logger


log = setup_logger()

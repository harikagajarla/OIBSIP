"""Small helper functions used across the project."""

import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import LOG_FILE

DB_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_HANDLER_FLAG = "_voice_assistant_handler"


def setup_logging(log_file=None, level=logging.INFO):
    """Send app log messages to a rotating log file."""
    logger = logging.getLogger("app")
    logger.setLevel(level)
    logger.propagate = False

    for handler in logger.handlers:
        if getattr(handler, _HANDLER_FLAG, False):
            return logger

    path = Path(log_file) if log_file else LOG_FILE

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            path,
            maxBytes=512_000,
            backupCount=2,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    except OSError:
        handler = logging.NullHandler()

    setattr(handler, _HANDLER_FLAG, True)
    logger.addHandler(handler)
    return logger


def shutdown_logging():
    """Close and remove the file handler."""
    logger = logging.getLogger("app")

    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_FLAG, False):
            logger.removeHandler(handler)
            handler.close()


_SMART_QUOTES = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
})


def normalize_text(text):
    """Lower-case, normalize quotes, collapse spaces and trim punctuation."""
    if not isinstance(text, str):
        return ""

    cleaned = text.translate(_SMART_QUOTES).lower()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.strip(" .,!?;")


def truncate(text, max_length):
    """Shorten text to max_length characters."""
    if max_length <= 3:
        return text[:max(max_length, 0)]

    if len(text) <= max_length:
        return text

    return text[:max_length - 3].rstrip() + "..."


def secret_status(value):
    """Return SET or MISSING without exposing the secret."""
    return "SET" if value else "MISSING"


_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}"
)

_HOST_PATTERN = re.compile(
    r"[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+"
)


def is_valid_email(address):
    """Practical email validation."""
    if not isinstance(address, str) or not 0 < len(address) <= 254:
        return False

    if not _EMAIL_PATTERN.fullmatch(address) or ".." in address:
        return False

    local_part = address.rsplit("@", 1)[0]
    return not (
        local_part.startswith(".")
        or local_part.endswith(".")
    )


def normalize_url(raw):
    """Return a safe HTTP/HTTPS URL or None."""
    if not isinstance(raw, str):
        return None

    candidate = raw.strip()

    if not candidate or any(char.isspace() for char in candidate):
        return None

    if "://" in candidate:
        scheme, _, rest = candidate.partition("://")

        if scheme.lower() not in ("http", "https"):
            return None
    else:
        if ":" in candidate:
            return None

        scheme, rest = "https", candidate

    host = re.split(r"[/?#]", rest, maxsplit=1)[0]

    if not _HOST_PATTERN.fullmatch(host):
        return None

    return f"{scheme.lower()}://{rest}"


def format_time(moment):
    """Format time like 9:05 AM."""
    return moment.strftime("%I:%M %p").lstrip("0")


def format_date(moment):
    """Format date like Tuesday, 29 September 2026."""
    return moment.strftime("%A, %d %B %Y")


def format_datetime(moment):
    """Format date and time for display."""
    return f"{format_date(moment)} at {format_time(moment)}"


def to_db_datetime(moment):
    """Convert datetime to SQLite text."""
    if moment.tzinfo is not None:
        moment = moment.astimezone().replace(tzinfo=None)

    return moment.strftime(DB_DATETIME_FORMAT)


def from_db_datetime(text):
    """Convert SQLite datetime text back to datetime."""
    return datetime.strptime(text, DB_DATETIME_FORMAT)

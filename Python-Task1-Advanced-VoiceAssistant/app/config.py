"""Central configuration: folder paths, constants, and settings read from .env.

Secrets (API key, email password) are read from environment variables only.
They are never written in source code and never printed or logged.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

APP_NAME = "Advanced Voice Assistant"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
ENV_FILE = BASE_DIR / ".env"
DB_PATH = DATA_DIR / "assistant.db"
LOG_FILE = LOG_DIR / "assistant.log"

DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
REQUEST_TIMEOUT_SECONDS = 10
REMINDER_CHECK_INTERVAL_SECONDS = 5
MAX_REMINDER_LENGTH = 200
MAX_COMMAND_NAME_LENGTH = 50
MAX_COMMAND_ACTION_LENGTH = 500


def load_environment(env_file=ENV_FILE):
    """Load variables from the .env file into the process environment."""
    path = Path(env_file)
    if load_dotenv is None or not path.is_file():
        return False
    return bool(load_dotenv(path, override=False, encoding="utf-8-sig"))


def ensure_directories():
    """Create the data/ and logs/ folders if they do not exist yet."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    """Settings taken from environment variables."""

    weather_api_key: str = field(default="", repr=False)
    smtp_email: str = field(default="", repr=False)
    smtp_app_password: str = field(default="", repr=False)
    smtp_server: str = DEFAULT_SMTP_SERVER
    smtp_port: int = DEFAULT_SMTP_PORT

    @property
    def weather_configured(self):
        return bool(self.weather_api_key)

    @property
    def email_configured(self):
        return bool(self.smtp_email and self.smtp_app_password)


def _read_env(name, default=""):
    return os.environ.get(name, default).strip()


def _read_port(name, default):
    """Read a TCP port number; fall back to the default if missing or invalid."""
    try:
        port = int(_read_env(name))
    except ValueError:
        return default
    return port if 1 <= port <= 65535 else default


def load_settings():
    """Build a Settings object from the current environment."""
    return Settings(
        weather_api_key=_read_env("WEATHER_API_KEY"),
        smtp_email=_read_env("SMTP_EMAIL"),
        smtp_app_password=_read_env("SMTP_APP_PASSWORD").replace(" ", ""),
        smtp_server=_read_env("SMTP_SERVER") or DEFAULT_SMTP_SERVER,
        smtp_port=_read_port("SMTP_PORT", DEFAULT_SMTP_PORT),
    )


load_environment()

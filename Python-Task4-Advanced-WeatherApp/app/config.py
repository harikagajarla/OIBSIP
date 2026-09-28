"""
Configuration loader.

Loads the OpenWeatherMap API key from a local .env file (never from
source code) and exposes shared constants used across the app.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a .env file sitting next to the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "").strip()

# --- API endpoints -----------------------------------------------------
CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
IP_GEOLOCATION_URL = "http://ip-api.com/json/"  # free, no key required

# --- Networking ----------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 10

# --- Database ------------------------------------------------------------
DATABASE_FILE = PROJECT_ROOT / "weather_app.db"

# --- App metadata --------------------------------------------------------
APP_TITLE = "Advanced Weather App"
AUTO_REFRESH_INTERVAL_MS = 10 * 60 * 1000  # 10 minutes, to limit API calls


class MissingAPIKeyError(RuntimeError):
    """Raised when no WEATHER_API_KEY is configured."""


def ensure_api_key_present() -> None:
    """Raise a clear, actionable error if the API key isn't set.

    Called once at startup so the app fails with a helpful message
    instead of crashing deep inside an HTTP call.
    """
    if not WEATHER_API_KEY:
        raise MissingAPIKeyError(
            "No WEATHER_API_KEY found.\n\n"
            "1. Copy .env.example to a new file named .env\n"
            "2. Open .env and paste your OpenWeatherMap API key\n"
            "3. Save the file and restart the app"
        )

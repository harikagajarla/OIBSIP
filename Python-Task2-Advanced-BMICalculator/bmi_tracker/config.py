"""Application-wide settings. No secrets are stored or needed in this project."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "bmi_records.db"

APP_TITLE = "BMI Tracker"

# Plausibility limits: they catch typos such as 175 (cm) typed into the metres field.
MIN_WEIGHT_KG = 2.0
MAX_WEIGHT_KG = 500.0
MIN_HEIGHT_M = 0.5
MAX_HEIGHT_M = 2.8

MAX_USERNAME_LENGTH = 40

# Category -> colour used for the result, the history table and the graph.
CATEGORY_COLOURS = {
    "Underweight": "#1E88E5",  # blue
    "Normal": "#2E7D32",  # green
    "Overweight": "#EF6C00",  # orange
    "Obese": "#C62828",  # red
}

# Text shown in the colour legend of the main window.
CATEGORY_RANGES = {
    "Underweight": "< 18.5",
    "Normal": "18.5 - 24.9",
    "Overweight": "25 - 29.9",
    "Obese": ">= 30",
}

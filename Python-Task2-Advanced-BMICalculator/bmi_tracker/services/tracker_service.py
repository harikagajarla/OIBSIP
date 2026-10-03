"""Service layer: the single entry point the UI uses.

It validates input, calls the core logic, stores results through the
database layer and prepares data for the graph.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from bmi_tracker.core.bmi import compute_bmi_result, validate_username
from bmi_tracker.db.database import Database, Record, User


def build_trend_series(records: Sequence[Record]) -> tuple[list[datetime], list[float]]:
    """Turn records into (dates, bmi_values) lists ordered oldest to newest."""
    ordered = sorted(records, key=lambda r: (r.recorded_at, r.id))
    return [r.recorded_at for r in ordered], [r.bmi for r in ordered]


class TrackerService:
    """Coordinates validation, calculation and storage."""

    def __init__(self, database: Database | None = None) -> None:
        self._db = database if database is not None else Database()

    def list_users(self) -> list[User]:
        return self._db.get_users()

    def create_user(self, name: str) -> User:
        """Validate the name, then store a new user."""
        return self._db.add_user(validate_username(name))

    def calculate_and_save(self, user_id: int, weight_text: str, height_text: str) -> Record:
        """Validate the raw input, calculate the BMI and save it for the user."""
        result = compute_bmi_result(weight_text, height_text)
        return self._db.add_record(
            user_id=user_id,
            weight_kg=result.weight_kg,
            height_m=result.height_m,
            bmi=result.bmi,
            category=result.category,
        )

    def get_history(self, user_id: int) -> list[Record]:
        """All saved records for the user, oldest first."""
        return self._db.get_records(user_id)

    def get_trend_data(self, user_id: int) -> tuple[list[datetime], list[float]]:
        """Dates and BMI values for the user's trend graph."""
        return build_trend_series(self._db.get_records(user_id))

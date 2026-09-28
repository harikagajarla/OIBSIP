"""
SQLite data access layer.

Two tables:
  - search_history: every successful search, most recent first
  - favorite_cities: user-starred cities

All queries are parameterized (no string-formatted SQL) to avoid
injection issues, even though this is a local single-user app.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app import config


@dataclass
class HistoryEntry:
    id: int
    city: str
    country: str
    searched_at: str
    temperature_c: float
    condition: str


@dataclass
class FavoriteCity:
    id: int
    city: str
    country: str


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection to the SQLite file, creating tables if needed."""
    path = db_path or config.DATABASE_FILE
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            country TEXT,
            searched_at TEXT NOT NULL,
            temperature_c REAL,
            condition TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS favorite_cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            country TEXT,
            UNIQUE(city, country)
        )
        """
    )
    conn.commit()


class SearchHistoryRepo:
    """Handles all reads/writes to the search_history table."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, city: str, country: str, temperature_c: float, condition: str) -> None:
        self._conn.execute(
            """
            INSERT INTO search_history (city, country, searched_at, temperature_c, condition)
            VALUES (?, ?, datetime('now', 'localtime'), ?, ?)
            """,
            (city, country, temperature_c, condition),
        )
        self._conn.commit()

    def get_recent(self, limit: int = 10) -> list[HistoryEntry]:
        rows = self._conn.execute(
            "SELECT * FROM search_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            HistoryEntry(
                id=row["id"],
                city=row["city"],
                country=row["country"] or "",
                searched_at=row["searched_at"],
                temperature_c=row["temperature_c"],
                condition=row["condition"] or "",
            )
            for row in rows
        ]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM search_history")
        self._conn.commit()


class FavoriteCitiesRepo:
    """Handles all reads/writes to the favorite_cities table."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add(self, city: str, country: str) -> bool:
        """Add a favorite. Returns False if it already exists (no error)."""
        try:
            self._conn.execute(
                "INSERT INTO favorite_cities (city, country) VALUES (?, ?)",
                (city, country),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # already a favorite

    def remove(self, city: str, country: str) -> None:
        self._conn.execute(
            "DELETE FROM favorite_cities WHERE city = ? AND country = ?",
            (city, country),
        )
        self._conn.commit()

    def get_all(self) -> list[FavoriteCity]:
        rows = self._conn.execute(
            "SELECT * FROM favorite_cities ORDER BY city ASC"
        ).fetchall()
        return [
            FavoriteCity(id=row["id"], city=row["city"], country=row["country"] or "")
            for row in rows
        ]

    def is_favorite(self, city: str, country: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM favorite_cities WHERE city = ? AND country = ?",
            (city, country),
        ).fetchone()
        return row is not None

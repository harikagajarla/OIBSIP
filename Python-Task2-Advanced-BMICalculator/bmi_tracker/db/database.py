"""SQLite storage for users and their BMI records.

This is the ONLY module that talks to the database. Every query is
parameterized (values are passed separately from the SQL text), and every
sqlite3 failure is converted into our own DatabaseError.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from bmi_tracker import config
from bmi_tracker.exceptions import DatabaseError, DuplicateUserError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    weight_kg   REAL NOT NULL CHECK (weight_kg > 0),
    height_m    REAL NOT NULL CHECK (height_m > 0),
    bmi         REAL NOT NULL,
    category    TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_records_user_time ON records (user_id, recorded_at);
"""


@dataclass(frozen=True)
class User:
    """A named person whose BMI history is stored."""

    id: int
    name: str
    created_at: datetime


@dataclass(frozen=True)
class Record:
    """One saved BMI measurement."""

    id: int
    user_id: int
    weight_kg: float
    height_m: float
    bmi: float
    category: str
    recorded_at: datetime


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise DatabaseError(f"The database contains an invalid date value: {value!r}") from exc


class Database:
    """Small wrapper around a SQLite file."""

    def __init__(self, db_path: Path | str = config.DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._initialise()

    # ------------------------------------------------------------------ setup
    def _initialise(self) -> None:
        """Create the data folder and the tables if they do not exist yet."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatabaseError(f"Could not create the data folder '{self.db_path.parent}': {exc}") from exc
        with self._connect("setting up the database") as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self, action: str) -> Iterator[sqlite3.Connection]:
        """Open a connection, commit on success, always close.

        Closing without a commit discards any half-finished changes, so a
        failed write never leaves partial data behind.
        """
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Database error while {action}: {exc}") from exc
        finally:
            if conn is not None:
                conn.close()

    # ------------------------------------------------------------------ users
    def add_user(self, name: str) -> User:
        """Insert a user. Names are unique, ignoring upper/lower case."""
        created = datetime.now().isoformat(timespec="seconds")
        with self._connect("saving the user") as conn:
            try:
                cursor = conn.execute(
                    "INSERT INTO users (name, created_at) VALUES (?, ?)", (name, created)
                )
            except sqlite3.IntegrityError as exc:
                if "UNIQUE" in str(exc).upper():
                    raise DuplicateUserError(f"A user named '{name}' already exists.") from exc
                raise
            user_id = cursor.lastrowid
        return User(id=int(user_id), name=name, created_at=datetime.fromisoformat(created))

    def get_users(self) -> list[User]:
        """Return all users sorted by name (case-insensitive)."""
        with self._connect("reading users") as conn:
            rows = conn.execute(
                "SELECT id, name, created_at FROM users ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [User(r["id"], r["name"], _parse_timestamp(r["created_at"])) for r in rows]

    def get_user_by_name(self, name: str) -> User | None:
        """Find a user by name (case-insensitive). Returns None if not found."""
        with self._connect("reading a user") as conn:
            row = conn.execute(
                "SELECT id, name, created_at FROM users WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
        if row is None:
            return None
        return User(row["id"], row["name"], _parse_timestamp(row["created_at"]))

    # ---------------------------------------------------------------- records
    def add_record(
        self,
        user_id: int,
        weight_kg: float,
        height_m: float,
        bmi: float,
        category: str,
        recorded_at: datetime | None = None,
    ) -> Record:
        """Save one BMI measurement for a user."""
        moment = recorded_at or datetime.now()
        stamp = moment.isoformat(timespec="seconds")
        with self._connect("saving the BMI record") as conn:
            cursor = conn.execute(
                "INSERT INTO records (user_id, weight_kg, height_m, bmi, category, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, weight_kg, height_m, bmi, category, stamp),
            )
            record_id = cursor.lastrowid
        return Record(
            id=int(record_id),
            user_id=user_id,
            weight_kg=weight_kg,
            height_m=height_m,
            bmi=bmi,
            category=category,
            recorded_at=datetime.fromisoformat(stamp),
        )

    def get_records(self, user_id: int) -> list[Record]:
        """Return a user's records, oldest first."""
        with self._connect("reading BMI history") as conn:
            rows = conn.execute(
                "SELECT id, user_id, weight_kg, height_m, bmi, category, recorded_at "
                "FROM records WHERE user_id = ? ORDER BY recorded_at, id",
                (user_id,),
            ).fetchall()
        return [
            Record(
                id=r["id"],
                user_id=r["user_id"],
                weight_kg=r["weight_kg"],
                height_m=r["height_m"],
                bmi=r["bmi"],
                category=r["category"],
                recorded_at=_parse_timestamp(r["recorded_at"]),
            )
            for r in rows
        ]

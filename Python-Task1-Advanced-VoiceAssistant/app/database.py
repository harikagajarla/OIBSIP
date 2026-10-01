"""SQLite database layer."""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.config import (
    DB_PATH,
    MAX_COMMAND_ACTION_LENGTH,
    MAX_COMMAND_NAME_LENGTH,
    MAX_REMINDER_LENGTH,
)
from app.models import CustomCommand, Reminder, ReminderStatus
from app.utils import from_db_datetime, normalize_text, to_db_datetime

logger = logging.getLogger(__name__)

_TRUE_VALUES = ("1", "true", "yes", "on")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    message       TEXT NOT NULL,
    reminder_time TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'done', 'cancelled')),
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reminders_status_time
    ON reminders (status, reminder_time);

CREATE TABLE IF NOT EXISTS custom_commands (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    command_name TEXT NOT NULL UNIQUE,
    action       TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class DatabaseError(Exception):
    """The database could not be used."""


class Database:
    """Reminders, custom commands and settings stored in one SQLite file."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)

    @contextmanager
    def _connect(self):
        """Open, commit, rollback on error, and always close the connection."""
        connection = None
        try:
            connection = sqlite3.connect(self.db_path, timeout=10)
            connection.row_factory = sqlite3.Row
            yield connection
            connection.commit()
        except sqlite3.Error as error:
            if connection is not None:
                connection.rollback()
            logger.error("Database operation failed: %s", error)
            raise DatabaseError(
                "The local database could not be accessed. Please try again."
            ) from error
        finally:
            if connection is not None:
                connection.close()

    def initialize(self):
        """Create the data folder and database tables."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            logger.error("Could not create data folder: %s", error)
            raise DatabaseError("The data folder could not be created.") from error

        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def is_healthy(self):
        """Return True if the database can be opened and queried."""
        try:
            with self._connect() as connection:
                connection.execute(
                    "SELECT name FROM sqlite_master LIMIT 1"
                ).fetchall()
            return True
        except DatabaseError:
            return False

    def add_reminder(self, message, reminder_time):
        """Save a new pending reminder and return it."""
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Reminder message cannot be empty.")

        text = message.strip()

        if len(text) > MAX_REMINDER_LENGTH:
            raise ValueError(
                f"Reminder message is too long "
                f"(maximum {MAX_REMINDER_LENGTH} characters)."
            )

        if not isinstance(reminder_time, datetime):
            raise ValueError("Reminder time is invalid.")

        when_text = to_db_datetime(reminder_time)
        created_text = to_db_datetime(datetime.now())

        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO reminders "
                "(message, reminder_time, status, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    text,
                    when_text,
                    ReminderStatus.PENDING,
                    created_text,
                ),
            )
            reminder_id = cursor.lastrowid

        return Reminder(
            id=reminder_id,
            message=text,
            reminder_time=from_db_datetime(when_text),
            status=ReminderStatus.PENDING,
            created_at=from_db_datetime(created_text),
        )

    def get_reminder(self, reminder_id):
        """Return one reminder or None."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (reminder_id,),
            ).fetchone()

        return self._to_reminder(row) if row else None

    def list_reminders(self, status=ReminderStatus.PENDING):
        """Return reminders ordered by time."""
        if status is not None and status not in ReminderStatus.ALL:
            raise ValueError(f"Unknown reminder status: {status!r}")

        query = "SELECT * FROM reminders"
        params = ()

        if status is not None:
            query += " WHERE status = ?"
            params = (status,)

        query += " ORDER BY reminder_time ASC, id ASC"

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        return [self._to_reminder(row) for row in rows]

    def get_due_reminders(self, now=None):
        """Return pending reminders whose time has arrived."""
        now_text = to_db_datetime(now or datetime.now())

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reminders "
                "WHERE status = ? AND reminder_time <= ? "
                "ORDER BY reminder_time ASC, id ASC",
                (ReminderStatus.PENDING, now_text),
            ).fetchall()

        return [self._to_reminder(row) for row in rows]

    def mark_reminder_done(self, reminder_id):
        """Change a pending reminder to done."""
        return self._change_pending_status(
            reminder_id,
            ReminderStatus.DONE,
        )

    def cancel_reminder(self, reminder_id):
        """Change a pending reminder to cancelled."""
        return self._change_pending_status(
            reminder_id,
            ReminderStatus.CANCELLED,
        )

    def delete_reminder(self, reminder_id):
        """Permanently remove a reminder."""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM reminders WHERE id = ?",
                (reminder_id,),
            )
            return cursor.rowcount > 0

    def _change_pending_status(self, reminder_id, new_status):
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE reminders "
                "SET status = ? "
                "WHERE id = ? AND status = ?",
                (
                    new_status,
                    reminder_id,
                    ReminderStatus.PENDING,
                ),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _to_reminder(row):
        return Reminder(
            id=row["id"],
            message=row["message"],
            reminder_time=from_db_datetime(row["reminder_time"]),
            status=row["status"],
            created_at=from_db_datetime(row["created_at"]),
        )

    def add_custom_command(self, command_name, action):
        """Save a custom command with a unique normalized name."""
        name = normalize_text(command_name)

        if not name:
            raise ValueError("Command name cannot be empty.")

        if len(name) > MAX_COMMAND_NAME_LENGTH:
            raise ValueError(
                f"Command name is too long "
                f"(maximum {MAX_COMMAND_NAME_LENGTH} characters)."
            )

        if not isinstance(action, str) or not action.strip():
            raise ValueError("Command action cannot be empty.")

        action_text = action.strip()

        if len(action_text) > MAX_COMMAND_ACTION_LENGTH:
            raise ValueError("Command action is too long.")

        created_text = to_db_datetime(datetime.now())

        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO custom_commands "
                    "(command_name, action, created_at) "
                    "VALUES (?, ?, ?)",
                    (
                        name,
                        action_text,
                        created_text,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError(
                    f"A custom command named '{name}' already exists."
                ) from error

            command_id = cursor.lastrowid

        return CustomCommand(
            id=command_id,
            command_name=name,
            action=action_text,
            created_at=from_db_datetime(created_text),
        )

    def get_custom_command(self, command_name):
        """Find a custom command by name."""
        name = normalize_text(command_name)

        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM custom_commands WHERE command_name = ?",
                (name,),
            ).fetchone()

        return self._to_custom_command(row) if row else None

    def list_custom_commands(self):
        """Return all custom commands alphabetically."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM custom_commands "
                "ORDER BY command_name ASC"
            ).fetchall()

        return [self._to_custom_command(row) for row in rows]

    def delete_custom_command(self, command_name):
        """Remove a custom command."""
        name = normalize_text(command_name)

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM custom_commands WHERE command_name = ?",
                (name,),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _to_custom_command(row):
        return CustomCommand(
            id=row["id"],
            command_name=row["command_name"],
            action=row["action"],
            created_at=from_db_datetime(row["created_at"]),
        )

    def get_setting(self, key, default=None):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()

        return row["value"] if row else default

    def set_setting(self, key, value):
        """Save a setting."""
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Setting name cannot be empty.")

        if isinstance(value, bool):
            value = "true" if value else "false"

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO settings (key, value) "
                "VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET "
                "value = excluded.value",
                (key.strip(), str(value)),
            )

    def get_bool_setting(self, key, default=False):
        raw = self.get_setting(key)

        if raw is None:
            return default

        return raw.strip().lower() in _TRUE_VALUES

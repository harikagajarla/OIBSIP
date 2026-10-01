"""Reminder management and background due-reminder checking."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Callable

from app.database import Database, DatabaseError
from app.models import Reminder, ReminderStatus
from app.time_parser import TimeParseError, parse_reminder_time

logger = logging.getLogger(__name__)


class ReminderManager:
    """High-level reminder service built on the existing SQLite database."""

    def __init__(self, database: Database | None = None):
        self.database = database or Database()
        self.database.initialize()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create(self, message: str, time_phrase: str, now: datetime | None = None) -> Reminder:
        """Create a future reminder from a natural-language time phrase."""
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Reminder message cannot be empty.")

        if not isinstance(time_phrase, str) or not time_phrase.strip():
            raise TimeParseError(
                "I couldn't find a time. Try something like 'at 6 PM' or 'in 10 minutes'."
            )

        reminder_time = parse_reminder_time(
            time_phrase.strip(),
            now=now or datetime.now(),
        )

        reminder = self.database.add_reminder(
            message=message.strip(),
            reminder_time=reminder_time,
        )

        logger.info(
            "Created reminder id=%s time=%s message=%r",
            reminder.id,
            reminder.reminder_time,
            reminder.message,
        )
        return reminder

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def list_pending(self) -> list[Reminder]:
        """Return all pending reminders ordered by time."""
        return self.database.list_reminders(ReminderStatus.PENDING)

    def list_all(self) -> list[Reminder]:
        """Return pending, done, and cancelled reminders."""
        return self.database.list_reminders(status=None)

    def get(self, reminder_id: int) -> Reminder | None:
        """Return one reminder by id."""
        return self.database.get_reminder(reminder_id)

    # ------------------------------------------------------------------
    # Cancel / complete
    # ------------------------------------------------------------------
    def cancel(self, reminder_id: int) -> bool:
        """Cancel a pending reminder."""
        changed = self.database.cancel_reminder(reminder_id)

        if changed:
            logger.info("Cancelled reminder id=%s", reminder_id)

        return changed

    def mark_done(self, reminder_id: int) -> bool:
        """Mark a pending reminder as completed."""
        changed = self.database.mark_reminder_done(reminder_id)

        if changed:
            logger.info("Completed reminder id=%s", reminder_id)

        return changed

    def delete(self, reminder_id: int) -> bool:
        """Permanently delete a reminder."""
        deleted = self.database.delete_reminder(reminder_id)

        if deleted:
            logger.info("Deleted reminder id=%s", reminder_id)

        return deleted

    # ------------------------------------------------------------------
    # Due reminders
    # ------------------------------------------------------------------
    def get_due(self, now: datetime | None = None) -> list[Reminder]:
        """Return pending reminders whose scheduled time has arrived."""
        return self.database.get_due_reminders(now=now or datetime.now())

    def consume_due(self, now: datetime | None = None) -> list[Reminder]:
        """
        Get due reminders and mark them done.

        The returned reminders are still available to the caller so the GUI
        or speech layer can announce them.
        """
        due = self.get_due(now=now)

        completed: list[Reminder] = []

        for reminder in due:
            try:
                if self.mark_done(reminder.id):
                    completed.append(reminder)
            except DatabaseError:
                logger.exception(
                    "Could not mark due reminder %s as done",
                    reminder.id,
                )

        return completed

    # ------------------------------------------------------------------
    # Background scheduler
    # ------------------------------------------------------------------
    def start_scheduler(
        self,
        on_due: Callable[[list[Reminder]], None],
        interval_seconds: float = 5.0,
    ) -> "ReminderScheduler":
        """
        Start a background reminder checker.

        `on_due` receives a list of reminders when one or more become due.
        """
        scheduler = ReminderScheduler(
            manager=self,
            on_due=on_due,
            interval_seconds=interval_seconds,
        )
        scheduler.start()
        return scheduler


class ReminderScheduler:
    """Background thread that checks for due reminders."""

    def __init__(
        self,
        manager: ReminderManager,
        on_due: Callable[[list[Reminder]], None],
        interval_seconds: float = 5.0,
    ):
        if not callable(on_due):
            raise TypeError("on_due must be callable.")

        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero.")

        self.manager = manager
        self.on_due = on_due
        self.interval_seconds = float(interval_seconds)

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        """Return True while the scheduler thread is active."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the scheduler once."""
        if self.is_running:
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="reminder-scheduler",
            daemon=True,
        )
        self._thread.start()

        logger.info(
            "Reminder scheduler started with %.1f second interval",
            self.interval_seconds,
        )

    def stop(self, timeout: float = 2.0) -> None:
        """Stop the scheduler."""
        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        logger.info("Reminder scheduler stopped.")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                due = self.manager.get_due()

                if due:
                    completed: list[Reminder] = []

                    for reminder in due:
                        try:
                            if self.manager.mark_done(reminder.id):
                                completed.append(reminder)
                        except DatabaseError:
                            logger.exception(
                                "Failed to complete due reminder id=%s",
                                reminder.id,
                            )

                    if completed:
                        try:
                            self.on_due(completed)
                        except Exception:
                            logger.exception(
                                "Reminder callback failed."
                            )

            except Exception:
                logger.exception("Reminder scheduler check failed.")

            self._stop_event.wait(self.interval_seconds)


def format_reminder(reminder: Reminder) -> str:
    """Convert one reminder to friendly display text."""
    formatted_time = reminder.reminder_time.strftime("%d %b %Y, %I:%M %p")
    return f"#{reminder.id} - {reminder.message} - {formatted_time}"


def format_reminders(reminders: list[Reminder]) -> str:
    """Convert a reminder list into assistant-friendly text."""
    if not reminders:
        return "You have no pending reminders."

    lines = ["Your pending reminders are:"]
    lines.extend(format_reminder(reminder) for reminder in reminders)
    return "\n".join(lines)
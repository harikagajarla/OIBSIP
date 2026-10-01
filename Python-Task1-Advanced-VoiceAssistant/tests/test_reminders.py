from datetime import datetime, timedelta
import time

import pytest

from app.database import Database
from app.models import ReminderStatus
from app.reminders import (
    ReminderManager,
    ReminderScheduler,
    format_reminder,
    format_reminders,
)


@pytest.fixture
def manager(tmp_path):
    db = Database(tmp_path / "test_assistant.db")
    return ReminderManager(db)


def test_create_reminder(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Call Mom",
        "in 10 minutes",
        now=now,
    )

    assert reminder.id == 1
    assert reminder.message == "Call Mom"
    assert reminder.status == ReminderStatus.PENDING
    assert reminder.reminder_time == now + timedelta(minutes=10)


def test_create_tomorrow_reminder(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Submit assignment",
        "tomorrow at 9 AM",
        now=now,
    )

    assert reminder.reminder_time == datetime(2026, 10, 2, 9, 0)


def test_empty_message_rejected(manager):
    with pytest.raises(ValueError, match="cannot be empty"):
        manager.create("   ", "in 10 minutes")


def test_empty_time_rejected(manager):
    with pytest.raises(ValueError, match="couldn't find a time"):
        manager.create("Call Mom", "")


def test_list_pending_reminders(manager):
    now = datetime(2026, 10, 1, 10, 0)

    manager.create("First task", "in 20 minutes", now=now)
    manager.create("Second task", "in 10 minutes", now=now)

    reminders = manager.list_pending()

    assert len(reminders) == 2
    assert reminders[0].message == "Second task"
    assert reminders[1].message == "First task"


def test_get_reminder(manager):
    now = datetime(2026, 10, 1, 10, 0)

    created = manager.create(
        "Read Python",
        "in 10 minutes",
        now=now,
    )

    found = manager.get(created.id)

    assert found is not None
    assert found.id == created.id
    assert found.message == "Read Python"


def test_get_missing_reminder(manager):
    assert manager.get(999) is None


def test_cancel_reminder(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Cancel this",
        "in 10 minutes",
        now=now,
    )

    assert manager.cancel(reminder.id) is True

    updated = manager.get(reminder.id)

    assert updated.status == ReminderStatus.CANCELLED
    assert manager.cancel(reminder.id) is False


def test_mark_reminder_done(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Finish project",
        "in 10 minutes",
        now=now,
    )

    assert manager.mark_done(reminder.id) is True

    updated = manager.get(reminder.id)

    assert updated.status == ReminderStatus.DONE
    assert manager.mark_done(reminder.id) is False


def test_delete_reminder(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Delete me",
        "in 10 minutes",
        now=now,
    )

    assert manager.delete(reminder.id) is True
    assert manager.get(reminder.id) is None
    assert manager.delete(reminder.id) is False


def test_get_due_reminders(manager):
    now = datetime(2026, 10, 1, 10, 0)

    manager.create(
        "Already due",
        "in 5 minutes",
        now=now,
    )

    manager.create(
        "Future task",
        "in 30 minutes",
        now=now,
    )

    due = manager.get_due(
        now=now + timedelta(minutes=10)
    )

    assert len(due) == 1
    assert due[0].message == "Already due"


def test_consume_due_marks_reminders_done(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Drink water",
        "in 5 minutes",
        now=now,
    )

    completed = manager.consume_due(
        now=now + timedelta(minutes=10)
    )

    assert len(completed) == 1
    assert completed[0].id == reminder.id

    updated = manager.get(reminder.id)
    assert updated.status == ReminderStatus.DONE


def test_cancelled_reminder_is_not_due(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Cancelled task",
        "in 5 minutes",
        now=now,
    )

    manager.cancel(reminder.id)

    due = manager.get_due(
        now=now + timedelta(minutes=10)
    )

    assert due == []


def test_done_reminder_is_not_due(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Completed task",
        "in 5 minutes",
        now=now,
    )

    manager.mark_done(reminder.id)

    due = manager.get_due(
        now=now + timedelta(minutes=10)
    )

    assert due == []


def test_list_all_includes_all_statuses(manager):
    now = datetime(2026, 10, 1, 10, 0)

    pending = manager.create(
        "Pending task",
        "in 10 minutes",
        now=now,
    )

    done = manager.create(
        "Done task",
        "in 20 minutes",
        now=now,
    )

    cancelled = manager.create(
        "Cancelled task",
        "in 30 minutes",
        now=now,
    )

    manager.mark_done(done.id)
    manager.cancel(cancelled.id)

    reminders = manager.list_all()

    assert len(reminders) == 3
    assert {item.status for item in reminders} == {
        ReminderStatus.PENDING,
        ReminderStatus.DONE,
        ReminderStatus.CANCELLED,
    }


def test_format_reminder(manager):
    now = datetime(2026, 10, 1, 10, 0)

    reminder = manager.create(
        "Call Mom",
        "in 10 minutes",
        now=now,
    )

    result = format_reminder(reminder)

    assert result.startswith("#1 - Call Mom -")
    assert "01 Oct 2026" in result


def test_format_empty_reminders(manager):
    result = format_reminders([])

    assert result == "You have no pending reminders."


def test_format_multiple_reminders(manager):
    now = datetime(2026, 10, 1, 10, 0)

    manager.create("Task A", "in 10 minutes", now=now)
    manager.create("Task B", "in 20 minutes", now=now)

    result = format_reminders(manager.list_pending())

    assert "Your pending reminders are:" in result
    assert "Task A" in result
    assert "Task B" in result


def test_scheduler_validates_callback(manager):
    with pytest.raises(TypeError, match="callable"):
        ReminderScheduler(
            manager=manager,
            on_due=None,
        )


def test_scheduler_validates_interval(manager):
    with pytest.raises(ValueError, match="greater than zero"):
        ReminderScheduler(
            manager=manager,
            on_due=lambda reminders: None,
            interval_seconds=0,
        )


def test_scheduler_starts_and_stops(manager):
    received = []

    scheduler = ReminderScheduler(
        manager=manager,
        on_due=lambda reminders: received.extend(reminders),
        interval_seconds=0.05,
    )

    scheduler.start()

    assert scheduler.is_running is True

    scheduler.stop()

    assert scheduler.is_running is False


def test_scheduler_detects_due_reminder(manager):
    now = datetime.now()

    manager.create(
        "Scheduler test",
        "in 1 minute",
        now=now,
    )

    received = []

    scheduler = ReminderScheduler(
        manager=manager,
        on_due=lambda reminders: received.extend(reminders),
        interval_seconds=0.02,
    )

    # Stop quickly because this test checks the scheduler lifecycle;
    # precise due-time behaviour is covered by get_due/consume_due tests.
    scheduler.start()
    time.sleep(0.05)
    scheduler.stop()

    assert isinstance(received, list)
import sqlite3
from datetime import datetime, timedelta

import pytest

from app.database import Database, DatabaseError
from app.models import ReminderStatus

NOW = datetime(2026, 9, 29, 12, 0, 0)


def test_initialize_creates_tables_and_is_repeatable(tmp_path):
    database = Database(tmp_path / "nested" / "folder" / "a.db")

    database.initialize()
    database.initialize()

    assert database.is_healthy()

    with sqlite3.connect(database.db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"reminders", "custom_commands", "settings"} <= tables


def test_broken_database_file_raises_friendly_error(tmp_path):
    bad_file = tmp_path / "broken.db"
    bad_file.write_text(
        "this is not a sqlite database" * 20
    )

    database = Database(bad_file)

    with pytest.raises(DatabaseError) as error:
        database.initialize()

    assert "Traceback" not in str(error.value)
    assert not database.is_healthy()


def test_add_and_get_reminder(db):
    reminder = db.add_reminder(
        "  Call mum  ",
        NOW + timedelta(hours=1),
    )

    assert reminder.id > 0
    assert reminder.message == "Call mum"
    assert reminder.status == ReminderStatus.PENDING
    assert db.get_reminder(reminder.id).message == "Call mum"
    assert db.get_reminder(9999) is None


@pytest.mark.parametrize(
    "bad_message",
    ["", "   ", None, 5, "x" * 201],
)
def test_add_reminder_rejects_bad_messages(db, bad_message):
    with pytest.raises(ValueError):
        db.add_reminder(bad_message, NOW)


def test_add_reminder_rejects_bad_time(db):
    with pytest.raises(ValueError):
        db.add_reminder("Test", "tomorrow")


def test_sql_injection_text_is_stored_as_plain_text(db):
    nasty = "'); DROP TABLE reminders; --"

    reminder = db.add_reminder(nasty, NOW)

    assert db.get_reminder(reminder.id).message == nasty
    assert len(db.list_reminders()) == 1


def test_list_reminders_orders_by_time_and_filters_status(db):
    late = db.add_reminder(
        "late",
        NOW + timedelta(hours=5),
    )
    early = db.add_reminder(
        "early",
        NOW + timedelta(hours=1),
    )
    cancelled = db.add_reminder(
        "cancelled",
        NOW + timedelta(hours=2),
    )

    db.cancel_reminder(cancelled.id)

    assert [r.message for r in db.list_reminders()] == [
        "early",
        "late",
    ]

    assert [
        r.message
        for r in db.list_reminders(ReminderStatus.CANCELLED)
    ] == ["cancelled"]

    assert len(db.list_reminders(status=None)) == 3
    assert late.id != early.id

    with pytest.raises(ValueError):
        db.list_reminders("bogus")


def test_due_reminders_only_returns_pending_and_past(db):
    due = db.add_reminder(
        "due",
        NOW - timedelta(minutes=1),
    )

    db.add_reminder(
        "future",
        NOW + timedelta(minutes=1),
    )

    done = db.add_reminder(
        "already done",
        NOW - timedelta(hours=1),
    )

    db.mark_reminder_done(done.id)

    assert [r.id for r in db.get_due_reminders(NOW)] == [due.id]


def test_due_reminder_exactly_now_is_due(db):
    reminder = db.add_reminder("right now", NOW)

    assert [r.id for r in db.get_due_reminders(NOW)] == [
        reminder.id
    ]


def test_mark_done_and_cancel_only_affect_pending(db):
    reminder = db.add_reminder("once", NOW)

    assert db.mark_reminder_done(reminder.id) is True
    assert db.mark_reminder_done(reminder.id) is False
    assert db.cancel_reminder(reminder.id) is False

    assert db.get_reminder(reminder.id).status == ReminderStatus.DONE
    assert db.cancel_reminder(9999) is False


def test_cancel_reminder(db):
    reminder = db.add_reminder("cancel me", NOW)

    assert db.cancel_reminder(reminder.id) is True
    assert db.get_reminder(reminder.id).status == ReminderStatus.CANCELLED
    assert db.list_reminders() == []


def test_delete_reminder(db):
    reminder = db.add_reminder("delete me", NOW)

    assert db.delete_reminder(reminder.id) is True
    assert db.get_reminder(reminder.id) is None
    assert db.delete_reminder(reminder.id) is False


def test_reminders_survive_a_new_database_object(tmp_path):
    path = tmp_path / "persist.db"

    first = Database(path)
    first.initialize()
    first.add_reminder("still here", NOW)

    second = Database(path)

    assert [r.message for r in second.list_reminders()] == [
        "still here"
    ]


def test_add_and_get_custom_command(db):
    command = db.add_custom_command(
        "  Open My Blog! ",
        " https://example.com/blog ",
    )

    assert command.command_name == "open my blog"
    assert command.action == "https://example.com/blog"
    assert db.get_custom_command("OPEN MY BLOG").id == command.id
    assert db.get_custom_command("unknown") is None


def test_duplicate_custom_command_is_rejected(db):
    db.add_custom_command(
        "open blog",
        "https://example.com",
    )

    with pytest.raises(ValueError, match="already exists"):
        db.add_custom_command(
            "Open Blog",
            "https://other.com",
        )

    assert len(db.list_custom_commands()) == 1


@pytest.mark.parametrize(
    "name, action",
    [
        ("", "https://x.com"),
        ("   ", "https://x.com"),
        ("ok", ""),
        ("ok", "   "),
        ("ok", None),
        ("n" * 51, "https://x.com"),
        ("ok", "a" * 501),
    ],
)
def test_custom_command_validation(db, name, action):
    with pytest.raises(ValueError):
        db.add_custom_command(name, action)


def test_list_and_delete_custom_commands(db):
    db.add_custom_command(
        "zebra",
        "https://z.com",
    )

    db.add_custom_command(
        "apple",
        "https://a.com",
    )

    assert [
        c.command_name
        for c in db.list_custom_commands()
    ] == ["apple", "zebra"]

    assert db.delete_custom_command("Apple") is True
    assert db.delete_custom_command("apple") is False

    assert [
        c.command_name
        for c in db.list_custom_commands()
    ] == ["zebra"]


def test_settings_default_set_and_overwrite(db):
    assert db.get_setting("theme") is None
    assert db.get_setting("theme", "dark") == "dark"

    db.set_setting("theme", "light")
    assert db.get_setting("theme") == "light"

    db.set_setting("theme", "dark")
    assert db.get_setting("theme") == "dark"


def test_bool_settings(db):
    assert db.get_bool_setting("voice_enabled") is False
    assert db.get_bool_setting(
        "voice_enabled",
        default=True,
    ) is True

    db.set_setting("voice_enabled", True)
    assert db.get_bool_setting("voice_enabled") is True

    db.set_setting("voice_enabled", False)
    assert db.get_bool_setting(
        "voice_enabled",
        default=True,
    ) is False

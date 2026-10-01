from datetime import datetime

from app.models import Intent, IntentName, Reminder, ReminderStatus, Response


def test_intent_defaults_are_independent():
    first = Intent(name=IntentName.GREETING)
    second = Intent(name=IntentName.TIME)

    first.entities["city"] = "Hyderabad"

    assert second.entities == {}
    assert not first.is_unknown


def test_unknown_intent_flag():
    assert Intent(name=IntentName.UNKNOWN).is_unknown


def test_response_helpers():
    good = Response.ok(
        "Hello",
        action="open_email_dialog",
        city="Hyderabad",
    )

    assert good.success
    assert good.action == "open_email_dialog"
    assert good.data == {"city": "Hyderabad"}

    bad = Response.error("Something went wrong")

    assert not bad.success
    assert bad.action is None
    assert bad.data == {}


def test_reminder_is_pending():
    now = datetime(2026, 9, 29, 18, 0)

    pending = Reminder(
        1,
        "Call mum",
        now,
        ReminderStatus.PENDING,
        now,
    )

    done = Reminder(
        2,
        "Call mum",
        now,
        ReminderStatus.DONE,
        now,
    )

    assert pending.is_pending
    assert not done.is_pending

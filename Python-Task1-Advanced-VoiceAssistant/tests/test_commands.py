from datetime import datetime

import pytest

from app.commands import CommandExecutor
from app.database import Database
from app.models import Intent, IntentName


@pytest.fixture
def executor(tmp_path):
    db = Database(tmp_path / "test_commands.db")
    return CommandExecutor(
        database=db,
        now_provider=lambda: datetime(2026, 10, 1, 10, 30),
    )


def make_intent(name, entities=None, raw_text=""):
    return Intent(
        name=name,
        confidence=1.0,
        entities=entities or {},
        raw_text=raw_text,
    )


# ------------------------------------------------------------------
# Basic responses
# ------------------------------------------------------------------

def test_greeting(executor):
    intent = make_intent(
        IntentName.GREETING,
        {"period": "morning"},
    )

    response = executor.execute(intent)

    assert response.success is True
    assert response.action == "greeting"
    assert "Good morning" in response.text


def test_goodbye(executor):
    response = executor.execute(
        make_intent(IntentName.GOODBYE)
    )

    assert response.success is True
    assert response.action == "exit"


def test_time(executor):
    response = executor.execute(
        make_intent(IntentName.TIME)
    )

    assert response.success is True
    assert response.action == "time"
    assert "10:30 AM" in response.text


def test_date(executor):
    response = executor.execute(
        make_intent(IntentName.DATE)
    )

    assert response.success is True
    assert response.action == "date"
    assert "01 October 2026" in response.text


def test_help(executor):
    response = executor.execute(
        make_intent(IntentName.HELP)
    )

    assert response.success is True
    assert response.action == "help"


def test_unknown(executor):
    response = executor.execute(
        make_intent(
            IntentName.UNKNOWN,
            raw_text="something random",
        )
    )

    assert response.success is False
    assert "didn't understand" in response.text


# ------------------------------------------------------------------
# FAQ
# ------------------------------------------------------------------

def test_faq_known_question(executor):
    response = executor.execute(
        make_intent(
            IntentName.FAQ,
            raw_text="What is Python?",
        )
    )

    assert response.success is True
    assert response.action == "faq"
    assert response.data["found"] is True
    assert "Python" in response.text


def test_faq_unknown_question(executor):
    response = executor.execute(
        make_intent(
            IntentName.FAQ,
            raw_text="What is quantum banana programming?",
        )
    )

    assert response.success is True
    assert response.data["found"] is False


# ------------------------------------------------------------------
# Reminders
# ------------------------------------------------------------------

def test_set_reminder(executor):
    response = executor.execute(
        make_intent(
            IntentName.SET_REMINDER,
            {
                "message": "Call Mom",
                "time_phrase": "in 10 minutes",
            },
        )
    )

    assert response.success is True
    assert response.action == "set_reminder"
    assert response.data["reminder_id"] == 1
    assert "Call Mom" in response.text


def test_set_reminder_missing_message(executor):
    response = executor.execute(
        make_intent(
            IntentName.SET_REMINDER,
            {
                "time_phrase": "in 10 minutes",
            },
        )
    )

    assert response.success is False


def test_set_reminder_missing_time(executor):
    response = executor.execute(
        make_intent(
            IntentName.SET_REMINDER,
            {
                "message": "Call Mom",
            },
        )
    )

    assert response.success is False


def test_list_reminders_empty(executor):
    response = executor.execute(
        make_intent(IntentName.LIST_REMINDERS)
    )

    assert response.success is True
    assert response.action == "list_reminders"
    assert response.data["count"] == 0
    assert "no pending reminders" in response.text.lower()


def test_list_reminders(executor):
    executor.execute(
        make_intent(
            IntentName.SET_REMINDER,
            {
                "message": "Study Python",
                "time_phrase": "in 10 minutes",
            },
        )
    )

    response = executor.execute(
        make_intent(IntentName.LIST_REMINDERS)
    )

    assert response.success is True
    assert response.data["count"] == 1
    assert "Study Python" in response.text


def test_cancel_reminder(executor):
    executor.execute(
        make_intent(
            IntentName.SET_REMINDER,
            {
                "message": "Cancel this",
                "time_phrase": "in 10 minutes",
            },
        )
    )

    response = executor.execute(
        make_intent(
            IntentName.CANCEL_REMINDER,
            {
                "reminder_id": 1,
            },
        )
    )

    assert response.success is True
    assert response.action == "cancel_reminder"
    assert response.data["reminder_id"] == 1


def test_cancel_missing_reminder(executor):
    response = executor.execute(
        make_intent(
            IntentName.CANCEL_REMINDER,
            {
                "reminder_id": 999,
            },
        )
    )

    assert response.success is False
    assert "couldn't find" in response.text.lower()


# ------------------------------------------------------------------
# Website safety
# ------------------------------------------------------------------

def test_invalid_website_is_rejected(executor):
    response = executor.execute(
        make_intent(
            IntentName.OPEN_WEBSITE,
            {"url": "file:///C:/secret.txt"},
        )
    )

    assert response.success is False


def test_missing_website(executor):
    response = executor.execute(
        make_intent(IntentName.OPEN_WEBSITE)
    )

    assert response.success is False


# ------------------------------------------------------------------
# Web search
# ------------------------------------------------------------------

def test_web_search_missing_query(executor):
    response = executor.execute(
        make_intent(
            IntentName.WEB_SEARCH,
            {"query": ""},
            raw_text="",
        )
    )

    assert response.success is False


# ------------------------------------------------------------------
# Email validation / form
# ------------------------------------------------------------------

def test_email_form_response(executor):
    response = executor.execute(
        make_intent(
            IntentName.SEND_EMAIL,
            {
                "recipient": "test@example.com",
            },
        )
    )

    assert response.success is True
    assert response.action == "email_form"
    assert response.data["recipient"] == "test@example.com"


def test_invalid_email_rejected(executor):
    response = executor.execute(
        make_intent(
            IntentName.SEND_EMAIL,
            {
                "recipient": "not-an-email",
                "subject": "Test",
                "message": "Hello",
            },
        )
    )

    assert response.success is False


# ------------------------------------------------------------------
# Weather without making a real API call
# ------------------------------------------------------------------

def test_weather_without_api_key(monkeypatch, executor):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("OWM_API_KEY", raising=False)
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)

    response = executor.execute(
        make_intent(
            IntentName.WEATHER,
            {"city": "Hyderabad"},
        )
    )

    assert response.success is False
    assert "API key" in response.text


def test_weather_missing_city(executor):
    response = executor.execute(
        make_intent(IntentName.WEATHER)
    )

    assert response.success is False
    assert "city" in response.text.lower()


# ------------------------------------------------------------------
# Custom commands
# ------------------------------------------------------------------

def test_custom_command_missing(executor):
    response = executor.execute(
        make_intent(
            IntentName.CUSTOM_COMMAND,
            {"command_name": "does not exist"},
        )
    )

    assert response.success is False
    assert "couldn't find" in response.text.lower()


def test_custom_command_executes_safe_action(executor):
    executor.database.add_custom_command(
        "what time",
        "what time is it",
    )

    response = executor.execute(
        make_intent(
            IntentName.CUSTOM_COMMAND,
            {"command_name": "what time"},
        )
    )

    assert response.success is True
    assert response.action == "time"
    assert "10:30 AM" in response.text


# ------------------------------------------------------------------
# Invalid Intent handling
# ------------------------------------------------------------------

def test_invalid_intent_object(executor):
    response = executor.execute("not an intent")

    assert response.success is False
    assert "process" in response.text.lower()
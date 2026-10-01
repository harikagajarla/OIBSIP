from app.intent import detect


def intent_name(result):
    name = result.name
    return name.value if hasattr(name, "value") else name


def test_greeting():
    result = detect("Hello")
    assert intent_name(result) == "greeting"


def test_good_morning_greeting():
    result = detect("Good morning")
    assert intent_name(result) == "greeting"
    assert result.entities.get("period") == "morning"


def test_time_request():
    result = detect("What time is it?")
    assert intent_name(result) == "time"


def test_date_request():
    result = detect("What is today's date?")
    assert intent_name(result) == "date"


def test_weather_with_city():
    result = detect("What is the weather in Hyderabad?")
    assert intent_name(result) == "weather"
    assert result.entities.get("city") == "Hyderabad"


def test_set_reminder():
    result = detect("Remind me to call mom tomorrow at 6 PM")
    assert intent_name(result) == "set_reminder"
    assert result.entities.get("message") == "call mom"
    assert result.entities.get("time_phrase") == "tomorrow at 6 PM"


def test_relative_reminder():
    result = detect("Remind me to drink water in 10 minutes")
    assert intent_name(result) == "set_reminder"
    assert result.entities.get("message") == "drink water"
    assert result.entities.get("time_phrase") == "in 10 minutes"


def test_list_reminders():
    result = detect("List my reminders")
    assert intent_name(result) == "list_reminders"


def test_cancel_reminder():
    result = detect("Cancel reminder 2")
    assert intent_name(result) == "cancel_reminder"


def test_web_search():
    result = detect("Search the web for Python tutorials")
    assert intent_name(result) == "web_search"
    assert "Python tutorials" in result.entities.get("query", "")


def test_open_website():
    result = detect("Open youtube.com")
    assert intent_name(result) == "open_website"


def test_open_calculator():
    result = detect("Open calculator")
    assert intent_name(result) == "open_website"
    assert result.entities.get("app") == "calculator"


def test_open_notepad():
    result = detect("Open notepad")
    assert intent_name(result) == "open_website"
    assert result.entities.get("app") == "notepad"


def test_send_email():
    result = detect("Send an email to test@example.com")
    assert intent_name(result) == "send_email"
    assert result.entities.get("recipient") == "test@example.com"


def test_faq_question():
    result = detect("What is Python?")
    assert intent_name(result) == "faq"


def test_how_to_question_uses_faq():
    result = detect("How do I set a reminder?")
    assert intent_name(result) == "faq"


def test_unknown_text():
    result = detect("xyzzy qwerty something completely unrelated")
    assert intent_name(result) == "unknown"


def test_empty_text():
    result = detect("")
    assert intent_name(result) == "unknown"


def test_none_input_does_not_raise():
    result = detect(None)
    assert intent_name(result) == "unknown"

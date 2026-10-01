from datetime import datetime, timedelta

import pytest

from app.time_parser import (
    TimeParseError,
    parse_reminder_time,
    split_reminder_text,
)


NOW = datetime(2026, 10, 1, 10, 0, 0)


def test_relative_minutes():
    result = parse_reminder_time("in 10 minutes", NOW)
    assert result == NOW + timedelta(minutes=10)


def test_relative_hours():
    result = parse_reminder_time("in 2 hours", NOW)
    assert result == NOW + timedelta(hours=2)


def test_relative_combined_duration():
    result = parse_reminder_time(
        "in 1 hour and 30 minutes",
        NOW,
    )
    assert result == NOW + timedelta(hours=1, minutes=30)


def test_relative_half_hour():
    result = parse_reminder_time(
        "in half an hour",
        NOW,
    )
    assert result == NOW + timedelta(minutes=30)


def test_relative_from_now():
    result = parse_reminder_time(
        "10 minutes from now",
        NOW,
    )
    assert result == NOW + timedelta(minutes=10)


def test_tomorrow_with_ampm():
    result = parse_reminder_time(
        "tomorrow at 9 AM",
        NOW,
    )
    assert result == datetime(2026, 10, 2, 9, 0)


def test_day_after_tomorrow():
    result = parse_reminder_time(
        "day after tomorrow at 10 AM",
        NOW,
    )
    assert result == datetime(2026, 10, 3, 10, 0)


def test_24_hour_time():
    result = parse_reminder_time(
        "tomorrow at 18:30",
        NOW,
    )
    assert result == datetime(2026, 10, 2, 18, 30)


def test_noon():
    result = parse_reminder_time(
        "tomorrow at noon",
        NOW,
    )
    assert result == datetime(2026, 10, 2, 12, 0)


def test_midnight():
    result = parse_reminder_time(
        "tomorrow at midnight",
        NOW,
    )
    assert result == datetime(2026, 10, 2, 0, 0)


def test_daypart_evening_resolves_time():
    result = parse_reminder_time(
        "tomorrow at 8 in the evening",
        NOW,
    )
    assert result == datetime(2026, 10, 2, 20, 0)


def test_bare_hour_requires_ampm():
    with pytest.raises(TimeParseError, match="AM or PM"):
        parse_reminder_time(
            "tomorrow at 6",
            NOW,
        )


def test_invalid_time():
    with pytest.raises(TimeParseError):
        parse_reminder_time(
            "tomorrow at 25:00",
            NOW,
        )


def test_invalid_minute():
    with pytest.raises(TimeParseError):
        parse_reminder_time(
            "tomorrow at 10:75",
            NOW,
        )


def test_past_explicit_date():
    with pytest.raises(TimeParseError, match="already passed"):
        parse_reminder_time(
            "today at 9 AM",
            NOW,
        )


def test_date_without_clock_requires_clock():
    with pytest.raises(TimeParseError, match="include a time"):
        parse_reminder_time(
            "tomorrow",
            NOW,
        )


def test_empty_time_phrase():
    with pytest.raises(TimeParseError):
        parse_reminder_time(
            "",
            NOW,
        )


def test_invalid_date():
    with pytest.raises(TimeParseError, match="doesn't exist"):
        parse_reminder_time(
            "31 February 2026 at 9 AM",
            NOW,
        )


def test_month_and_day():
    result = parse_reminder_time(
        "5 October 2026 at 4 PM",
        NOW,
    )
    assert result == datetime(2026, 10, 5, 16, 0)


def test_month_day_format():
    result = parse_reminder_time(
        "October 5th, 2026 at 4 PM",
        NOW,
    )
    assert result == datetime(2026, 10, 5, 16, 0)


def test_weekday():
    result = parse_reminder_time(
        "Friday at 5 PM",
        NOW,
    )
    assert result == datetime(2026, 10, 2, 17, 0)


def test_next_weekday():
    result = parse_reminder_time(
        "next Monday at 9 AM",
        NOW,
    )
    assert result == datetime(2026, 10, 5, 9, 0)


def test_split_reminder_text():
    message, phrase = split_reminder_text(
        "remind me to call mom at 6 PM"
    )

    assert message == "remind me to call mom"
    assert phrase == "at 6 PM"


def test_split_multiple_time_parts():
    message, phrase = split_reminder_text(
        "remind me tomorrow to call mom at 6 PM"
    )

    assert message == "remind me to call mom"
    assert phrase == "tomorrow at 6 PM"


def test_split_without_time():
    message, phrase = split_reminder_text(
        "remind me to call mom"
    )

    assert message == "remind me to call mom"
    assert phrase is None

import logging
from datetime import datetime, timedelta, timezone

import pytest

from app import utils


def test_normalize_text_cleans_case_spaces_and_punctuation():
    assert utils.normalize_text("  What's   the TIME? ") == "what's the time"
    assert utils.normalize_text("Hello!!!") == "hello"
    assert utils.normalize_text("What\u2019s up") == "what's up"


def test_normalize_text_keeps_times_and_handles_bad_input():
    assert utils.normalize_text("Remind me at 6:30 PM.") == "remind me at 6:30 pm"
    assert utils.normalize_text(None) == ""
    assert utils.normalize_text(123) == ""


def test_truncate():
    assert utils.truncate("short", 10) == "short"
    assert utils.truncate("a" * 20, 10) == "a" * 7 + "..."
    assert utils.truncate("abcdef", 3) == "abc"


def test_secret_status_never_shows_value():
    assert utils.secret_status("abc123") == "SET"
    assert utils.secret_status("") == "MISSING"
    assert utils.secret_status(None) == "MISSING"


@pytest.mark.parametrize(
    "address",
    [
        "a@b.co",
        "first.last@example.com",
        "user+tag@mail.example.org",
    ],
)
def test_valid_emails(address):
    assert utils.is_valid_email(address)


@pytest.mark.parametrize(
    "address",
    [
        "",
        "plainaddress",
        "user@domain",
        "user name@x.com",
        "a..b@x.com",
        ".a@x.com",
        "a.@x.com",
        "user@x.c",
        "@x.com",
        "user@",
        "a@b.com\nBcc: x@y.com",
        None,
        42,
    ],
)
def test_invalid_emails(address):
    assert not utils.is_valid_email(address)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("youtube.com", "https://youtube.com"),
        (
            "  www.github.com/features  ",
            "https://www.github.com/features",
        ),
        (
            "https://www.google.com/search?q=python",
            "https://www.google.com/search?q=python",
        ),
        ("http://example.org", "http://example.org"),
        ("HTTPS://Example.com", "https://Example.com"),
    ],
)
def test_normalize_url_accepts_web_addresses(raw, expected):
    assert utils.normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "not a url",
        "localhost",
        "javascript:alert(1)",
        "mailto:a@b.com",
        "file:///C:/secret.txt",
        "ftp://example.com",
        "https://user@evil.com",
        "example.com:8080",
        "https://example.com:8080",
        "https://",
        None,
        5,
    ],
)
def test_normalize_url_rejects_unsafe_input(raw):
    assert utils.normalize_url(raw) is None


def test_time_and_date_formatting():
    moment = datetime(2026, 9, 29, 18, 30)

    assert utils.format_time(moment) == "6:30 PM"
    assert utils.format_date(moment) == "Tuesday, 29 September 2026"
    assert (
        utils.format_datetime(moment)
        == "Tuesday, 29 September 2026 at 6:30 PM"
    )


def test_time_formatting_edge_cases():
    assert utils.format_time(datetime(2026, 1, 1, 0, 5)) == "12:05 AM"
    assert utils.format_time(datetime(2026, 1, 1, 9, 5)) == "9:05 AM"
    assert utils.format_time(datetime(2026, 1, 1, 12, 0)) == "12:00 PM"


def test_db_datetime_round_trip_drops_microseconds():
    moment = datetime(2026, 9, 29, 18, 30, 15, 999999)

    text = utils.to_db_datetime(moment)

    assert text == "2026-09-29 18:30:15"
    assert utils.from_db_datetime(text) == datetime(
        2026, 9, 29, 18, 30, 15
    )


def test_db_datetime_converts_timezone_aware_values():
    aware = datetime(
        2026,
        9,
        29,
        12,
        0,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )

    assert utils.from_db_datetime(
        utils.to_db_datetime(aware)
    ).tzinfo is None


def test_from_db_datetime_rejects_garbage():
    with pytest.raises(ValueError):
        utils.from_db_datetime("not a date")


def test_setup_logging_writes_file_and_is_idempotent(tmp_path):
    log_file = tmp_path / "logs" / "test.log"

    try:
        logger = utils.setup_logging(log_file)
        utils.setup_logging(log_file)

        flagged = [
            handler
            for handler in logger.handlers
            if getattr(handler, "_voice_assistant_handler", False)
        ]

        assert len(flagged) == 1

        logging.getLogger("app.test").info("hello log file")

        for handler in logger.handlers:
            handler.flush()

        assert "hello log file" in log_file.read_text(
            encoding="utf-8"
        )
    finally:
        utils.shutdown_logging()

"""Understand reminder times written in everyday language."""

import re
from datetime import date, datetime, time, timedelta

MAX_DAYS_AHEAD = 366


class TimeParseError(ValueError):
    """The time could not be understood."""


_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
}

_UNIT_SECONDS = {
    "second": 1, "sec": 1, "minute": 60, "min": 60,
    "hour": 3600, "hr": 3600, "day": 86400, "week": 604800,
}

_MSG_NO_TIME = "I couldn't find a time. Try something like 'at 6 PM' or 'in 10 minutes'."
_MSG_NEED_CLOCK = "Please include a time as well, for example 'tomorrow at 9 AM'."
_MSG_NEED_AMPM = "Please include AM or PM, for example '6 PM' (or use 24-hour time like 18:00)."
_MSG_INVALID_TIME = "That doesn't look like a valid time."
_MSG_PAST = "That time has already passed. Please give me a time in the future."
_MSG_TOO_FAR = "That is too far ahead. I can set reminders up to one year in advance."
_MSG_BAD_DATE = "That date doesn't exist."


def _alternatives(words):
    return "|".join(sorted(words, key=len, reverse=True))


_MONTH_NAMES = _alternatives(_MONTHS)
_WEEKDAY_NAMES = _alternatives(_WEEKDAYS)
_NUMBER_WORD_NAMES = _alternatives(_NUMBER_WORDS)

_UNIT = r"(?:seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?)"
_CHUNK = rf"\b(?:\d+(?:\.\d+)?\s*|(?:half an?|half|{_NUMBER_WORD_NAMES})\s+){_UNIT}\b"
_DURATION = rf"{_CHUNK}(?:(?:\s*,\s*|\s+and\s+|\s+){_CHUNK})*(?:\s+and\s+a\s+half)?"
_RELATIVE = rf"(?:\bin\s+{_DURATION}(?:\s+from\s+now)?|{_DURATION}\s+from\s+now)"

_ON_FOR = r"(?:(?:on|for)\s+)?"
_DATE_WORD = (
    rf"\b{_ON_FOR}(?:day after tomorrow|tomorrow|yesterday|today|tonight"
    r"|this (?:morning|afternoon|evening))\b"
)
_WEEKDAY = rf"\b{_ON_FOR}(?:next\s+)?(?:{_WEEKDAY_NAMES})\b"
_DAY_MONTH = (
    rf"\b{_ON_FOR}(?:the\s+)?\d{{1,2}}(?:st|nd|rd|th)?(?:\s+of)?\s+(?:{_MONTH_NAMES})\b"
    r"(?:,?\s+\d{4}\b)?"
)
_MONTH_DAY = (
    rf"\b{_ON_FOR}(?:{_MONTH_NAMES})\s+\d{{1,2}}(?:st|nd|rd|th)?\b"
    r"(?:,?\s+\d{4}\b)?"
)
_ISO_DATE = rf"\b{_ON_FOR}\d{{4}}-\d{{2}}-\d{{2}}\b"

_MERIDIEM = r"[ap]\.?m\b\.?"
_AT_FOR = r"(?:(?:at|for|around)\s+)?"
_CLOCK_AMPM = rf"\b{_AT_FOR}\d{{1,2}}(?::\d{{2}})?\s*{_MERIDIEM}"
_CLOCK_COLON = rf"\b{_AT_FOR}\d{{1,2}}:\d{{2}}\b"
_CLOCK_AT_HOUR = r"\bat\s+\d{1,2}(?:\s*o'?clock)?\b"
_CLOCK_WORD = rf"\b{_AT_FOR}(?:noon|midnight)\b"
_DAYPART = r"\b(?:in the (?:morning|afternoon|evening)|at night|tonight|this (?:morning|afternoon|evening))\b"

_SPAN_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        _RELATIVE, _DATE_WORD, _WEEKDAY, _DAY_MONTH, _MONTH_DAY, _ISO_DATE,
        _CLOCK_AMPM, _CLOCK_COLON, _CLOCK_AT_HOUR, _CLOCK_WORD, _DAYPART,
    )
]

_CHUNK_PARTS = re.compile(
    rf"\b(?:(?P<digits>\d+(?:\.\d+)?)\s*|(?P<words>half an?|half|{_NUMBER_WORD_NAMES})\s+)"
    rf"(?P<unit>{_UNIT})\b",
    re.IGNORECASE,
)

_RELATIVE_RE = re.compile(_RELATIVE, re.IGNORECASE)
_AND_A_HALF = re.compile(r"\band\s+a\s+half\b", re.IGNORECASE)

_AMPM_RE = re.compile(
    r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<mer>[ap])\.?m\b\.?",
    re.IGNORECASE,
)

_COLON_RE = re.compile(
    r"\b(?P<hour>\d{1,2}):(?P<minute>\d{2})\b(?!\s*[ap]\.?m\b)",
    re.IGNORECASE,
)

_AT_HOUR_RE = re.compile(
    r"\bat\s+(?P<hour>\d{1,2})(?:\s*o'?clock)?\b(?!\s*(?::\d|[ap]\.?m\b))",
    re.IGNORECASE,
)

_WORD_RE = re.compile(
    r"\b(?P<word>noon|midnight)\b",
    re.IGNORECASE,
)

_DAYPART_RE = re.compile(
    r"\b(?:in the (?P<part>morning|afternoon|evening)|(?P<night>at night|tonight)"
    r"|this (?P<part2>morning|afternoon|evening))\b",
    re.IGNORECASE,
)

_DATE_WORD_RE = re.compile(
    r"\b(?P<word>day after tomorrow|tomorrow|yesterday|today|tonight"
    r"|this (?:morning|afternoon|evening))\b",
    re.IGNORECASE,
)

_ISO_RE = re.compile(
    r"\b(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\b"
)

_DAY_MONTH_RE = re.compile(
    rf"\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?(?:\s+of)?\s+(?P<month>{_MONTH_NAMES})\b"
    r"(?:,?\s+(?P<year>\d{4})\b)?",
    re.IGNORECASE,
)

_MONTH_DAY_RE = re.compile(
    rf"\b(?P<month>{_MONTH_NAMES})\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\b"
    r"(?:,?\s+(?P<year>\d{4})\b)?",
    re.IGNORECASE,
)

_WEEKDAY_RE = re.compile(
    rf"\b(?P<next>next\s+)?(?P<day>{_WEEKDAY_NAMES})\b",
    re.IGNORECASE,
)


def split_reminder_text(text):
    """Separate time words from the rest of a reminder sentence."""
    if not isinstance(text, str):
        return "", None

    spans = []

    for pattern in _SPAN_PATTERNS:
        spans.extend(match.span() for match in pattern.finditer(text))

    if not spans:
        return _tidy(text), None

    spans.sort()
    merged = [spans[0]]

    for start, end in spans[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    phrase = " ".join(
        text[start:end]
        for start, end in merged
    )

    pieces = []
    cursor = 0

    for start, end in merged:
        pieces.append(text[cursor:start])
        cursor = end

    pieces.append(text[cursor:])

    return _tidy("".join(pieces)), phrase


def _tidy(text):
    """Clean spacing and remove dangling connector words."""
    cleaned = re.sub(r"\s+", " ", text).strip(" ,;:.-")
    cleaned = re.sub(
        r"(?:\s+(?:and|at|on|in|for|by|to|around|please))+$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" ,;:.-")


def parse_reminder_time(text, now=None):
    """Convert a human-readable time phrase into a future datetime."""
    if not isinstance(text, str) or not text.strip():
        raise TimeParseError(_MSG_NO_TIME)

    now = (now or datetime.now()).replace(microsecond=0)
    phrase = " ".join(text.split())

    relative = _parse_relative(phrase, now)

    if relative is not None:
        return relative

    clock = _find_clock(phrase)
    date_info = _find_date(phrase, now.date())

    if clock is None:
        if date_info is None:
            raise TimeParseError(_MSG_NO_TIME)
        raise TimeParseError(_MSG_NEED_CLOCK)

    hour, minute = clock

    if date_info is None:
        result = datetime.combine(
            now.date(),
            time(hour, minute),
        )

        if result <= now:
            result += timedelta(days=1)
    else:
        day, roll_weekly = date_info

        result = datetime.combine(
            day,
            time(hour, minute),
        )

        if result <= now:
            if not roll_weekly:
                raise TimeParseError(_MSG_PAST)

            result += timedelta(days=7)

    if result - now > timedelta(days=MAX_DAYS_AHEAD):
        raise TimeParseError(_MSG_TOO_FAR)

    return result


def _parse_relative(phrase, now):
    """Parse relative durations such as 'in 2 hours'."""
    match = _RELATIVE_RE.search(phrase)

    if match is None:
        return None

    body = match.group(0)
    total_seconds = 0.0
    last_unit_seconds = 0

    for chunk in _CHUNK_PARTS.finditer(body):
        if chunk.group("digits"):
            quantity = float(chunk.group("digits"))
        else:
            words = chunk.group("words").lower()
            quantity = (
                0.5
                if words.startswith("half")
                else _NUMBER_WORDS[words]
            )

        unit = chunk.group("unit").lower().rstrip("s")
        last_unit_seconds = _UNIT_SECONDS[unit]
        total_seconds += quantity * last_unit_seconds

    if _AND_A_HALF.search(body):
        total_seconds += 0.5 * last_unit_seconds

    if total_seconds <= 0:
        raise TimeParseError(
            "Please give me a duration longer than zero, like 'in 10 minutes'."
        )

    if total_seconds > MAX_DAYS_AHEAD * 86400:
        raise TimeParseError(_MSG_TOO_FAR)

    return now + timedelta(seconds=round(total_seconds))


def _find_clock(phrase):
    """Return a clock time as (hour, minute)."""
    candidates = []

    for match in _AMPM_RE.finditer(phrase):
        candidates.append(
            (
                match.start(),
                match.group("hour"),
                match.group("minute"),
                match.group("mer").lower() + "m",
                None,
            )
        )

    for match in _COLON_RE.finditer(phrase):
        candidates.append(
            (
                match.start(),
                match.group("hour"),
                match.group("minute"),
                None,
                None,
            )
        )

    for match in _AT_HOUR_RE.finditer(phrase):
        candidates.append(
            (
                match.start(),
                match.group("hour"),
                None,
                None,
                None,
            )
        )

    for match in _WORD_RE.finditer(phrase):
        fixed = (
            (12, 0)
            if match.group("word").lower() == "noon"
            else (0, 0)
        )

        candidates.append(
            (
                match.start(),
                None,
                None,
                None,
                fixed,
            )
        )

    if not candidates:
        return None

    _, hour_text, minute_text, meridiem, fixed = max(
        candidates,
        key=lambda item: item[0],
    )

    if fixed is not None:
        return fixed

    return _to_24_hour(
        hour_text,
        minute_text,
        meridiem,
        _find_daypart(phrase),
    )


def _find_daypart(phrase):
    match = _DAYPART_RE.search(phrase)

    if match is None:
        return None

    if match.group("night"):
        return "night"

    part = (
        match.group("part")
        or match.group("part2")
    ).lower()

    return "am" if part == "morning" else "pm"


def _to_24_hour(hour_text, minute_text, meridiem, daypart):
    hour = int(hour_text)
    minute = int(minute_text) if minute_text else 0

    if minute > 59:
        raise TimeParseError(_MSG_INVALID_TIME)

    if meridiem:
        if not 1 <= hour <= 12:
            raise TimeParseError(_MSG_INVALID_TIME)

        if meridiem == "am":
            return (0 if hour == 12 else hour), minute

        return (12 if hour == 12 else hour + 12), minute

    if hour > 23:
        raise TimeParseError(_MSG_INVALID_TIME)

    if (
        hour >= 13
        or hour == 0
        or (
            len(hour_text) == 2
            and hour_text.startswith("0")
        )
    ):
        return hour, minute

    if daypart == "am":
        return (0 if hour == 12 else hour), minute

    if daypart == "pm":
        return (12 if hour == 12 else hour + 12), minute

    if daypart == "night":
        if hour == 12:
            return 0, minute

        return (
            hour + 12 if hour >= 6 else hour,
            minute,
        )

    raise TimeParseError(_MSG_NEED_AMPM)


def _find_date(phrase, today):
    """Return (date, roll_weekly) or None."""
    match = _DATE_WORD_RE.search(phrase)

    if match:
        word = match.group("word").lower()

        offsets = {
            "day after tomorrow": 2,
            "tomorrow": 1,
            "yesterday": -1,
        }

        return today + timedelta(
            days=offsets.get(word, 0)
        ), False

    match = _ISO_RE.search(phrase)

    if match:
        return (
            _make_date(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
                today,
            ),
            False,
        )

    for pattern in (
        _DAY_MONTH_RE,
        _MONTH_DAY_RE,
    ):
        match = pattern.search(phrase)

        if match:
            year = (
                int(match.group("year"))
                if match.group("year")
                else None
            )

            month = _MONTHS[
                match.group("month").lower()
            ]

            return (
                _make_date(
                    year,
                    month,
                    int(match.group("day")),
                    today,
                ),
                False,
            )

    match = _WEEKDAY_RE.search(phrase)

    if match:
        target = _WEEKDAYS[
            match.group("day").lower()
        ]

        days_ahead = (
            target - today.weekday()
        ) % 7

        is_next = bool(match.group("next"))

        if is_next and days_ahead == 0:
            days_ahead = 7

        return (
            today + timedelta(days=days_ahead),
            not is_next and days_ahead == 0,
        )

    return None


def _make_date(year, month, day, today):
    try:
        result = date(
            year or today.year,
            month,
            day,
        )

        if year is None and result < today:
            result = date(
                today.year + 1,
                month,
                day,
            )

    except ValueError:
        raise TimeParseError(_MSG_BAD_DATE) from None

    return result

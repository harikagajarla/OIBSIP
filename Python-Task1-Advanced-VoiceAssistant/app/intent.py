"""Rule-based intent detection for the Advanced Voice Assistant."""

import logging
import re
from dataclasses import dataclass

from app.knowledge_base import KnowledgeBase
from app.models import Intent, IntentName
from app.time_parser import split_reminder_text
from app.utils import is_valid_email, normalize_text, normalize_url

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.5
STRONG_CONFIDENCE = 0.9

BUILTIN_APPS = {
    "calculator": ("calculator", "calc"),
    "notepad": ("notepad", "text editor"),
    "vscode": (
        "vs code",
        "vscode",
        "visual studio code",
    ),
    "browser": (
        "browser",
        "web browser",
        "internet browser",
    ),
}

_APP_LOOKUP = {
    alias: key
    for key, aliases in BUILTIN_APPS.items()
    for alias in aliases
}

_APP_ALTERNATIVES = "|".join(
    sorted(_APP_LOOKUP, key=len, reverse=True)
)


@dataclass(frozen=True)
class _Rule:
    intent: str
    patterns: tuple
    extractor: object = None

    def score(self, normalized):
        best = 0.0

        for regex, weight in self.patterns:
            if regex.search(normalized):
                best = max(best, weight)

        return best


def _p(pattern, weight):
    return re.compile(pattern, re.IGNORECASE), weight


def _clean_raw(raw):
    return (
        re.sub(r"\s+", " ", raw)
        .strip()
        .rstrip(".?!,;")
        .strip()
    )


def _extract_greeting(raw, normalized):
    match = re.search(
        r"\bgood\s+(morning|afternoon|evening)\b",
        normalized,
    )

    return {
        "period": match.group(1)
    } if match else {}


def _extract_time(raw, normalized):
    return {
        "include_date": "yes"
    } if "date" in normalized else {}


_WEATHER_WORDS = re.compile(
    r"\b(?:weather|temperature|forecast|"
    r"raining|sunny|cloudy|snowing|windy|"
    r"hot|cold|warm|humid)\b",
    re.IGNORECASE,
)

_CITY_TRAILING = re.compile(
    r"(?:\s+(?:today|tonight|tomorrow|now|"
    r"right now|currently|please|outside|like|"
    r"this week|this morning|this evening|"
    r"this afternoon|at the moment|for me|again))+$",
    re.IGNORECASE,
)

_CITY_FILLER = {
    "what",
    "whats",
    "what's",
    "is",
    "the",
    "tell",
    "me",
    "show",
    "give",
    "check",
    "current",
    "currently",
    "today",
    "todays",
    "today's",
    "how",
    "hows",
    "how's",
    "like",
    "now",
    "please",
    "can",
    "you",
    "get",
    "find",
    "fetch",
    "of",
    "for",
    "in",
    "at",
    "a",
    "an",
    "hey",
    "hello",
    "hi",
    "ok",
    "okay",
    "will",
    "be",
    "it",
    "do",
    "i",
    "want",
    "to",
    "know",
    "see",
    "about",
    "and",
    "report",
    "update",
    "latest",
    "live",
    "outside",
    "near",
}


def _clean_city(text):
    previous = None

    while previous != text:
        previous = text
        text = _CITY_TRAILING.sub(
            "",
            text,
        ).strip(" ,.?!")

    if (
        not text
        or len(text) > 60
        or len(text.split()) > 5
        or not re.search(r"[A-Za-z]", text)
    ):
        return ""

    return text.title()


def _extract_weather(raw, normalized):
    keyword = _WEATHER_WORDS.search(raw)

    if keyword is None:
        return {}

    after = raw[keyword.end():]

    match = re.search(
        r"\b(?:in|at|for|of|near)\s+(.+)$",
        after,
        re.IGNORECASE,
    )

    if match:
        city = _clean_city(match.group(1))

        return {"city": city} if city else {}

    leftovers = [
        word
        for word in raw[:keyword.start()].split()
        if word.lower() not in _CITY_FILLER
    ]

    if 1 <= len(leftovers) <= 4:
        city = _clean_city(
            " ".join(leftovers)
        )

        return {"city": city} if city else {}

    return {}


_REMINDER_PREFIX = re.compile(
    r"^\s*"
    r"(?:(?:hey|ok|okay)[ ,]+)?"
    r"(?:(?:can|could|would|will) you\s+)?"
    r"(?:please\s+)?"
    r"(?:remind me|"
    r"(?:set|add|create|make|schedule)"
    r"\s+(?:a\s+|an\s+|the\s+)?"
    r"(?:new\s+)?"
    r"(?:reminder|alarm)|"
    r"(?:a\s+|an\s+|the\s+)?"
    r"(?:new\s+)?reminder)"
    r"(?:\s+(?:to|that|about|of|for|on))?"
    r"\s*[:,-]?\s*",
    re.IGNORECASE,
)


def _extract_set_reminder(raw, normalized):
    message, phrase = split_reminder_text(raw)

    message = _REMINDER_PREFIX.sub(
        "",
        message,
        count=1,
    )

    message = re.sub(
        r"^(?:to|that|about)\s+",
        "",
        message,
        flags=re.IGNORECASE,
    )

    return {
        "message": message.strip(),
        "time_phrase": phrase,
    }


def _extract_search(raw, normalized):
    patterns = (
        r"^(?:search|google|look up|find)\s+(?:for\s+)?(.+)$",
        r"^(?:can you|please|could you)\s+"
        r"(?:search|google|look up|find)\s+"
        r"(?:for\s+)?(.+)$",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            raw,
            re.IGNORECASE,
        )

        if match:
            return {
                "query": match.group(1).strip()
            }

    return {}


def _extract_open_website(raw, normalized):
    url_match = re.search(
        r"(https?://[^\s]+|"
        r"(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?)",
        raw,
        re.IGNORECASE,
    )

    if url_match:
        url = normalize_url(
            url_match.group(1).rstrip(".,!?")
        )

        if url:
            return {
                "url": url
            }

    match = re.search(
        r"\b(?:open|go to|visit)\s+"
        r"(.+)$",
        raw,
        re.IGNORECASE,
    )

    if match:
        target = match.group(1).strip()
        url = normalize_url(target)

        if url:
            return {
                "url": url
            }

    return {}


def _extract_app(raw, normalized):
    match = re.search(
        rf"\b(?:open|launch|start|run)\s+"
        rf"(?P<app>{_APP_ALTERNATIVES})\b",
        normalized,
        re.IGNORECASE,
    )

    if not match:
        return {}

    alias = match.group("app").lower()

    return {
        "app": _APP_LOOKUP.get(alias)
    }


def _extract_cancel_reminder(raw, normalized):
    match = re.search(
        r"\b(?:cancel|delete|remove)"
        r"\s+(?:reminder\s+)?"
        r"(?P<id>\d+)\b",
        normalized,
        re.IGNORECASE,
    )

    if not match:
        return {}

    return {
        "reminder_id": int(match.group("id"))
    }


def _extract_email(raw, normalized):
    emails = re.findall(
        r"[A-Za-z0-9._%+\-]+@"
        r"[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*"
        r"\.[A-Za-z]{2,}",
        raw,
    )

    valid = [
        address
        for address in emails
        if is_valid_email(address)
    ]

    return {
        "recipient": valid[0]
    } if valid else {}


def _extract_custom_command(raw, normalized):
    match = re.search(
        r"\b(?:run|execute|use)\s+"
        r"(?:my\s+)?(.+)$",
        raw,
        re.IGNORECASE,
    )

    if match:
        return {
            "command_name": normalize_text(
                match.group(1)
            )
        }

    return {}


_RULES = (
    _Rule(
        IntentName.GREETING,
        (
            _p(
                r"^(?:hi|hello|hey|good\s+"
                r"morning|good\s+afternoon|"
                r"good\s+evening)\b",
                0.95,
            ),
        ),
        _extract_greeting,
    ),

    _Rule(
        IntentName.GOODBYE,
        (
            _p(
                r"^(?:bye|goodbye|good\s+night|"
                r"see you|see ya|quit|exit)\b",
                0.95,
            ),
        ),
    ),

    _Rule(
        IntentName.HELP,
        (
            _p(
                r"^(?:help|commands|"
                r"what can i say|what can i ask)\b",
                0.95,
            ),
        ),
    ),

    _Rule(
        IntentName.DATE,
        (
            _p(
                r"\b(?:what is|what's|tell me|"
                r"show me|give me)\s+"
                r"(?:today's\s+|todays\s+)?(?:the\s+)?(?:date|day)\b",
                0.95,
            ),
            _p(r"\bwhat day is it\b", 0.95),
        ),
        _extract_time,
    ),

    _Rule(
        IntentName.TIME,
        (
            _p(
                r"\b(?:what time|current time|"
                r"time is it|tell me the time)\b",
                0.95,
            ),
            _p(r"\btime\b", 0.55),
        ),
        _extract_time,
    ),

    _Rule(
        IntentName.WEATHER,
        (
            _p(
                r"\b(?:weather|temperature|"
                r"forecast|raining|sunny|cloudy|"
                r"snowing|windy|humid)\b",
                0.95,
            ),
        ),
        _extract_weather,
    ),

    _Rule(
        IntentName.SET_REMINDER,
        (
            _p(
                r"\bremind me\b",
                0.98,
            ),
            _p(
                r"\b(?:set|add|create|make|"
                r"schedule)\s+(?:a\s+)?"
                r"(?:new\s+)?(?:reminder|alarm)\b",
                0.98,
            ),
            _p(
                r"^\s*(?:a\s+)?(?:new\s+)?"
                r"reminder\b",
                0.9,
            ),
        ),
        _extract_set_reminder,
    ),

    _Rule(
        IntentName.LIST_REMINDERS,
        (
            _p(
                r"\b(?:list|show|view|see)\s+"
                r"(?:my\s+)?reminders\b",
                0.98,
            ),
            _p(
                r"\bwhat are my reminders\b",
                0.98,
            ),
        ),
    ),

    _Rule(
        IntentName.CANCEL_REMINDER,
        (
            _p(
                r"\b(?:cancel|delete|remove)"
                r"\s+(?:reminder|alarm)\b",
                0.98,
            ),
        ),
        _extract_cancel_reminder,
    ),

    _Rule(
        IntentName.SEND_EMAIL,
        (
            _p(
                r"\b(?:send|write|compose)"
                r"\s+(?:an?\s+)?email\b",
                0.98,
            ),
            _p(
                r"\bemail\s+(?:this|someone|"
                r"him|her|them)\b",
                0.9,
            ),
        ),
        _extract_email,
    ),

    _Rule(
        IntentName.WEB_SEARCH,
        (
            _p(
                r"\b(?:search|google|look up|"
                r"find)\b",
                0.95,
            ),
        ),
        _extract_search,
    ),

    _Rule(
        IntentName.OPEN_WEBSITE,
        (
            _p(
                r"\b(?:open|go to|visit)"
                r"\s+(?:https?://|www\.)",
                0.98,
            ),
            _p(
                r"\b(?:open|go to|visit)"
                r"\s+[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                0.95,
            ),
        ),
        _extract_open_website,
    ),

    _Rule(
        IntentName.OPEN_WEBSITE,
        (
            _p(
                r"\b(?:open|launch|start|"
                r"run)\s+(?:calculator|"
                r"calc|notepad|text editor|"
                r"vs code|vscode|visual studio code|"
                r"browser|web browser|"
                r"internet browser)\b",
                0.95,
            ),
        ),
        _extract_app,
    ),

    _Rule(
        IntentName.CUSTOM_COMMAND,
        (
            _p(
                r"\b(?:run|execute|use)"
                r"\s+(?:my\s+)?\w+",
                0.75,
            ),
        ),
        _extract_custom_command,
    ),
)


def _looks_like_how_to_question(normalized):
    return bool(
        re.search(
            r"^(?:how\s+(?:do|does|can|could|"
            r"should|would)\b|how\s+to\b)",
            normalized,
        )
    )


def _faq_intent(text, knowledge_base):
    if knowledge_base is None:
        return None

    match = knowledge_base.find(text)

    if match is None:
        return None

    return Intent(
        name=IntentName.FAQ,
        confidence=match.score,
        entities={
            "faq_id": match.entry.id,
            "answer": match.entry.answer,
        },
        raw_text=text,
    )


def detect(text, knowledge_base=None):
    """Detect an intent without ever raising an exception."""
    try:
        if not isinstance(text, str):
            return Intent(
                name=IntentName.UNKNOWN,
                confidence=0.0,
                raw_text="",
            )

        raw = _clean_raw(text)
        normalized = normalize_text(raw)

        if not normalized:
            return Intent(
                name=IntentName.UNKNOWN,
                confidence=0.0,
                raw_text=raw,
            )

        kb = (
            knowledge_base
            if knowledge_base is not None
            else KnowledgeBase.default()
        )

        if (
            _looks_like_how_to_question(
                normalized
            )
            or normalized.endswith("?")
        ):
            faq_result = _faq_intent(
                raw,
                kb,
            )

            if faq_result is not None:
                return faq_result

        best_rule = None
        best_score = 0.0

        for rule in _RULES:
            score = rule.score(normalized)

            if score > best_score:
                best_rule = rule
                best_score = score

        if (
            best_rule is None
            or best_score < MIN_CONFIDENCE
        ):
            faq_result = _faq_intent(
                raw,
                kb,
            )

            if faq_result is not None:
                return faq_result

            return Intent(
                name=IntentName.UNKNOWN,
                confidence=0.0,
                raw_text=raw,
            )

        entities = {}

        if best_rule.extractor:
            try:
                entities = best_rule.extractor(
                    raw,
                    normalized,
                ) or {}
            except Exception as error:
                logger.warning(
                    "Intent extraction failed: %s",
                    error,
                )
                entities = {}

        return Intent(
            name=best_rule.intent,
            confidence=best_score,
            entities=entities,
            raw_text=raw,
        )

    except Exception as error:
        logger.exception(
            "Intent detection failed"
        )

        return Intent(
            name=IntentName.UNKNOWN,
            confidence=0.0,
            raw_text=(
                text
                if isinstance(text, str)
                else ""
            ),
        )


class IntentDetector:
    """Reusable detector object for the application."""

    def __init__(self, knowledge_base=None):
        self.knowledge_base = (
            knowledge_base
            or KnowledgeBase.default()
        )

    def detect(self, text):
        return detect(
            text,
            self.knowledge_base,
        )


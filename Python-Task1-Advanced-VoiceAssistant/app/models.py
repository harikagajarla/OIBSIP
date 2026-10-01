"""Small data classes shared by every part of the assistant."""

from dataclasses import dataclass, field
from datetime import datetime


class IntentName:
    """Names of every intent the assistant understands."""

    GREETING = "greeting"
    GOODBYE = "goodbye"
    TIME = "time"
    DATE = "date"
    OPEN_WEBSITE = "open_website"
    WEB_SEARCH = "web_search"
    WEATHER = "weather"
    SET_REMINDER = "set_reminder"
    LIST_REMINDERS = "list_reminders"
    CANCEL_REMINDER = "cancel_reminder"
    SEND_EMAIL = "send_email"
    FAQ = "faq"
    CUSTOM_COMMAND = "custom_command"
    HELP = "help"
    UNKNOWN = "unknown"


class ReminderStatus:
    """Allowed values for a reminder's status column."""

    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"
    ALL = (PENDING, DONE, CANCELLED)


@dataclass
class Intent:
    """The result of intent detection for one user message."""

    name: str
    confidence: float = 0.0
    entities: dict = field(default_factory=dict)
    raw_text: str = ""

    @property
    def is_unknown(self):
        return self.name == IntentName.UNKNOWN


@dataclass
class Response:
    """What the assistant answers, plus an optional request for the UI."""

    text: str
    success: bool = True
    action: str | None = None
    data: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, text, action=None, **data):
        return cls(text=text, success=True, action=action, data=data)

    @classmethod
    def error(cls, text):
        return cls(text=text, success=False)


@dataclass
class Reminder:
    """One row of the reminders table."""

    id: int
    message: str
    reminder_time: datetime
    status: str
    created_at: datetime

    @property
    def is_pending(self):
        return self.status == ReminderStatus.PENDING


@dataclass
class CustomCommand:
    """One row of the custom_commands table."""

    id: int
    command_name: str
    action: str
    created_at: datetime

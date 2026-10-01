"""Command execution layer for the Advanced Voice Assistant."""

from __future__ import annotations

import logging
import os
import re
import shutil
import smtplib
import subprocess
import webbrowser
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import quote_plus, urlparse

import requests

from app.database import Database
from app.knowledge_base import KnowledgeBase
from app.models import Intent, IntentName, Response
from app.reminders import ReminderManager, format_reminders

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Execute an Intent and return a user-facing Response."""

    def __init__(
        self,
        database: Database | None = None,
        reminder_manager: ReminderManager | None = None,
        knowledge_base: KnowledgeBase | None = None,
        now_provider=None,
    ):
        self.database = database or Database()
        self.database.initialize()

        self.reminders = reminder_manager or ReminderManager(self.database)
        self.knowledge_base = knowledge_base or KnowledgeBase.default()
        self.now_provider = now_provider or datetime.now

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def execute(self, intent: Intent) -> Response:
        """Execute one detected intent safely."""
        if not isinstance(intent, Intent):
            return Response.error("I could not process that command.")

        handlers = {
            IntentName.GREETING: self._greeting,
            IntentName.GOODBYE: self._goodbye,
            IntentName.TIME: self._time,
            IntentName.DATE: self._date,
            IntentName.OPEN_WEBSITE: self._open_website,
            IntentName.WEB_SEARCH: self._web_search,
            IntentName.WEATHER: self._weather,
            IntentName.SET_REMINDER: self._set_reminder,
            IntentName.LIST_REMINDERS: self._list_reminders,
            IntentName.CANCEL_REMINDER: self._cancel_reminder,
            IntentName.SEND_EMAIL: self._send_email,
            IntentName.FAQ: self._faq,
            IntentName.CUSTOM_COMMAND: self._custom_command,
            IntentName.HELP: self._help,
            IntentName.UNKNOWN: self._unknown,
        }

        handler = handlers.get(intent.name)

        if handler is None:
            return Response.error("I don't know how to handle that command yet.")

        try:
            return handler(intent)
        except Exception:
            logger.exception(
                "Command failed. intent=%s raw_text=%r",
                intent.name,
                intent.raw_text,
            )
            return Response.error(
                "Something went wrong while handling that command."
            )

    # ------------------------------------------------------------------
    # Basic commands
    # ------------------------------------------------------------------
    @staticmethod
    def _greeting(intent: Intent) -> Response:
        period = intent.entities.get("period")

        if period == "morning":
            text = "Good morning. How can I help you?"
        elif period == "afternoon":
            text = "Good afternoon. How can I help you?"
        elif period == "evening":
            text = "Good evening. How can I help you?"
        else:
            text = "Hello. How can I help you?"

        return Response.ok(text, action="greeting")

    @staticmethod
    def _goodbye(intent: Intent) -> Response:
        return Response.ok(
            "Goodbye. Have a great day.",
            action="exit",
        )

    def _time(self, intent: Intent) -> Response:
        current = self.now_provider()
        return Response.ok(
            f"The current time is {current.strftime('%I:%M %p')}.",
            action="time",
            time=current.strftime("%I:%M %p"),
        )

    def _date(self, intent: Intent) -> Response:
        current = self.now_provider()
        return Response.ok(
            f"Today's date is {current.strftime('%d %B %Y')}.",
            action="date",
            date=current.strftime("%d %B %Y"),
        )

    @staticmethod
    def _help(intent: Intent) -> Response:
        text = (
            "You can ask me the time or date, check weather, set or list "
            "reminders, cancel a reminder, search the web, open a website "
            "or app, send an email, or ask one of my built-in questions."
        )

        return Response.ok(
            text,
            action="help",
        )

    @staticmethod
    def _unknown(intent: Intent) -> Response:
        return Response.error(
            "I didn't understand that. Say help to see examples."
        )

    # ------------------------------------------------------------------
    # Website / search
    # ------------------------------------------------------------------
    def _open_website(self, intent: Intent) -> Response:
        entities = intent.entities or {}

        app_name = self._first_entity(
            entities,
            "app",
            "name",
            "application",
        )

        if app_name:
            return self._open_builtin_app(str(app_name))

        url = self._first_entity(
            entities,
            "url",
            "website",
            "site",
        )

        if not url:
            return Response.error(
                "Which website would you like me to open?"
            )

        safe_url = self._safe_url(str(url))

        if safe_url is None:
            return Response.error(
                "I can only open normal web addresses."
            )

        webbrowser.open(safe_url)

        return Response.ok(
            f"Opening {safe_url}.",
            action="open_website",
            url=safe_url,
        )

    def _open_builtin_app(self, app_name: str) -> Response:
        key = app_name.strip().lower()

        aliases = {
            "calculator": "calculator",
            "calc": "calculator",
            "notepad": "notepad",
            "text editor": "notepad",
            "vscode": "vscode",
            "vs code": "vscode",
            "visual studio code": "vscode",
            "browser": "browser",
            "web browser": "browser",
            "internet browser": "browser",
        }

        resolved = aliases.get(key)

        if resolved is None:
            return Response.error(
                f"I don't have permission to open the app '{app_name}'."
            )

        try:
            if resolved == "calculator":
                subprocess.Popen(["calc.exe"])

            elif resolved == "notepad":
                subprocess.Popen(["notepad.exe"])

            elif resolved == "vscode":
                code_path = shutil.which("code")

                if not code_path:
                    return Response.error(
                        "Visual Studio Code was not found in PATH."
                    )

                subprocess.Popen([code_path])

            elif resolved == "browser":
                webbrowser.open("https://www.google.com")

        except OSError:
            logger.exception("Could not open built-in app %s", resolved)
            return Response.error(
                f"I couldn't open {resolved} on this computer."
            )

        return Response.ok(
            f"Opening {resolved}.",
            action="open_app",
            app=resolved,
        )

    @staticmethod
    def _web_search(intent: Intent) -> Response:
        entities = intent.entities or {}

        query = CommandExecutor._first_entity(
            entities,
            "query",
            "search_query",
            "text",
        )

        if not query:
            query = intent.raw_text.strip()

            query = re.sub(
                r"^\s*(?:please\s+)?(?:search|google|look up|find)\s+",
                "",
                query,
                flags=re.IGNORECASE,
            )

        query = str(query).strip()

        if not query:
            return Response.error(
                "What would you like me to search for?"
            )

        url = (
            "https://www.google.com/search?q="
            + quote_plus(query)
        )

        webbrowser.open(url)

        return Response.ok(
            f"Searching the web for {query}.",
            action="web_search",
            query=query,
            url=url,
        )

    # ------------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------------
    def _weather(self, intent: Intent) -> Response:
        entities = intent.entities or {}

        city = self._first_entity(
            entities,
            "city",
            "location",
        )

        if not city:
            return Response.error(
                "Please tell me the city, for example: weather in Hyderabad."
            )

        api_key = (
            os.getenv("OPENWEATHER_API_KEY")
            or os.getenv("OWM_API_KEY")
            or os.getenv("WEATHER_API_KEY")
        )

        if not api_key:
            return Response.error(
                "The weather API key is not configured yet."
            )

        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": city,
                    "appid": api_key,
                    "units": "metric",
                },
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("Weather request failed.")
            return Response.error(
                "I couldn't reach the weather service right now."
            )

        if response.status_code == 401:
            return Response.error(
                "The weather API key is invalid."
            )

        if response.status_code == 404:
            return Response.error(
                f"I couldn't find weather information for {city}."
            )

        if response.status_code != 200:
            return Response.error(
                "The weather service returned an error."
            )

        try:
            data = response.json()

            description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]

            text = (
                f"In {data.get('name', city)}, it is "
                f"{temperature:.0f} degrees Celsius with {description}. "
                f"It feels like {feels_like:.0f} degrees, "
                f"with {humidity}% humidity."
            )

            return Response.ok(
                text,
                action="weather",
                city=data.get("name", city),
                temperature=temperature,
                feels_like=feels_like,
                humidity=humidity,
                description=description,
            )

        except (KeyError, TypeError, ValueError):
            logger.exception("Unexpected weather response.")
            return Response.error(
                "I received an unexpected weather response."
            )

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------
    def _set_reminder(self, intent: Intent) -> Response:
        entities = intent.entities or {}

        message = self._first_entity(
            entities,
            "message",
            "reminder_message",
            "text",
        )

        time_phrase = self._first_entity(
            entities,
            "time_phrase",
            "time",
            "when",
            "reminder_time",
        )

        if not message or not time_phrase:
            return Response.error(
                "Please include both what I should remind you about "
                "and when. For example: remind me to call Mom at 6 PM."
            )

        try:
            reminder = self.reminders.create(
                message=str(message),
                time_phrase=str(time_phrase),
                now=self.now_provider(),
            )
        except ValueError as error:
            return Response.error(str(error))
        except Exception:
            logger.exception("Reminder creation failed.")
            return Response.error(
                "I couldn't create that reminder."
            )

        formatted = reminder.reminder_time.strftime(
            "%d %B %Y at %I:%M %p"
        )

        return Response.ok(
            f"Reminder set for {formatted}: {reminder.message}.",
            action="set_reminder",
            reminder_id=reminder.id,
            reminder_time=reminder.reminder_time.isoformat(),
            message=reminder.message,
        )

    def _list_reminders(self, intent: Intent) -> Response:
        reminders = self.reminders.list_pending()

        return Response.ok(
            format_reminders(reminders),
            action="list_reminders",
            count=len(reminders),
            reminders=reminders,
        )

    def _cancel_reminder(self, intent: Intent) -> Response:
        entities = intent.entities or {}

        reminder_id = self._first_entity(
            entities,
            "reminder_id",
            "id",
            "number",
        )

        if reminder_id is None:
            return Response.error(
                "Please tell me the reminder number to cancel."
            )

        try:
            reminder_id = int(reminder_id)
        except (TypeError, ValueError):
            return Response.error(
                "The reminder number is invalid."
            )

        reminder = self.reminders.get(reminder_id)

        if reminder is None:
            return Response.error(
                f"I couldn't find reminder number {reminder_id}."
            )

        if self.reminders.cancel(reminder_id):
            return Response.ok(
                f"Cancelled reminder {reminder_id}: {reminder.message}.",
                action="cancel_reminder",
                reminder_id=reminder_id,
            )

        return Response.error(
            f"Reminder {reminder_id} is no longer pending."
        )

    # ------------------------------------------------------------------
    # FAQ / knowledge base
    # ------------------------------------------------------------------
    def _faq(self, intent: Intent) -> Response:
        question = intent.raw_text.strip()

        if not question:
            return Response.error(
                "Please ask me a question."
            )

        answer = self.knowledge_base.answer(question)

        if answer is None:
            return Response.ok(
                "I don't know that yet. My built-in knowledge base only "
                "contains a limited set of topics.",
                action="faq",
                found=False,
            )

        return Response.ok(
            answer,
            action="faq",
            found=True,
        )

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------
    def _send_email(self, intent: Intent) -> Response:
        entities = intent.entities or {}

        recipient = self._first_entity(
            entities,
            "recipient",
            "email",
            "email_address",
            "to",
        )

        subject = self._first_entity(
            entities,
            "subject",
        )

        message = self._first_entity(
            entities,
            "message",
            "body",
            "email_message",
        )

        # The GUI can use this response to open an email form.
        if not recipient or not subject or not message:
            return Response.ok(
                "Please enter the recipient, subject, and message.",
                action="email_form",
                recipient=recipient or "",
                subject=subject or "",
                message=message or "",
            )

        if not self._valid_email(str(recipient)):
            return Response.error(
                "That email address does not look valid."
            )

        sender = os.getenv("EMAIL_ADDRESS")
        password = os.getenv("EMAIL_PASSWORD")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port_text = os.getenv("SMTP_PORT", "587")

        if not sender or not password:
            return Response.error(
                "Email is not configured yet. Add EMAIL_ADDRESS and "
                "EMAIL_PASSWORD to the local environment file."
            )

        try:
            smtp_port = int(smtp_port_text)
        except ValueError:
            return Response.error(
                "The email SMTP port is invalid."
            )

        email = EmailMessage()
        email["From"] = sender
        email["To"] = str(recipient)
        email["Subject"] = str(subject)
        email.set_content(str(message))

        try:
            with smtplib.SMTP(
                smtp_host,
                smtp_port,
                timeout=15,
            ) as smtp:
                smtp.starttls()
                smtp.login(sender, password)
                smtp.send_message(email)

        except (OSError, smtplib.SMTPException):
            logger.exception("Email sending failed.")
            return Response.error(
                "I couldn't send the email. Please check your "
                "email settings."
            )

        return Response.ok(
            f"Email sent to {recipient}.",
            action="send_email",
            recipient=str(recipient),
        )

    # ------------------------------------------------------------------
    # Custom commands
    # ------------------------------------------------------------------
    def _custom_command(self, intent: Intent) -> Response:
        entities = intent.entities or {}

        command_name = self._first_entity(
            entities,
            "command_name",
            "name",
            "command",
        )

        if not command_name:
            command_name = intent.raw_text.strip()

        custom = self.database.get_custom_command(
            str(command_name)
        )

        if custom is None:
            return Response.error(
                f"I couldn't find a custom command named "
                f"'{command_name}'."
            )

        # Custom actions are treated as assistant-language commands.
        # They are passed back through intent detection rather than
        # executed as arbitrary shell commands.
        try:
            from app.intent import detect

            action_intent = detect(custom.action)

            if action_intent.is_unknown:
                return Response.error(
                    "That custom command points to an unsupported action."
                )

            return self.execute(action_intent)

        except Exception:
            logger.exception(
                "Custom command execution failed: %s",
                custom.command_name,
            )
            return Response.error(
                "I couldn't execute that custom command."
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _first_entity(entities: dict, *names):
        for name in names:
            value = entities.get(name)
            if value is not None and str(value).strip():
                return value
        return None

    @staticmethod
    def _safe_url(url: str) -> str | None:
        candidate = url.strip()

        if not candidate:
            return None

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidate):
            candidate = "https://" + candidate

        parsed = urlparse(candidate)

        if parsed.scheme not in {"http", "https"}:
            return None

        if not parsed.netloc:
            return None

        return candidate

    @staticmethod
    def _valid_email(value: str) -> bool:
        return bool(
            re.fullmatch(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                value.strip(),
            )
        )
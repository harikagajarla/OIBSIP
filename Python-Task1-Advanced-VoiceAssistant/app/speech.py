"""Speech input and text-to-speech output for the Advanced Voice Assistant."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import pyttsx3
import speech_recognition as sr

logger = logging.getLogger(__name__)


class SpeechError(Exception):
    """Base class for speech-related errors."""


class MicrophoneUnavailableError(SpeechError):
    """The default microphone could not be opened."""


class SpeechTimeoutError(SpeechError):
    """No speech was detected before the timeout."""


class SpeechRecognitionError(SpeechError):
    """The spoken audio could not be understood."""


class SpeechServiceUnavailableError(SpeechError):
    """The online speech-recognition service could not be reached."""


@dataclass(frozen=True)
class SpeechResult:
    """Result of one speech-recognition attempt."""

    text: str
    success: bool = True
    error_code: str | None = None


class SpeechService:
    """
    Handle microphone input and offline text-to-speech.

    The microphone always uses the Windows default input device.
    No device index is hard-coded.
    """

    def __init__(
        self,
        recognizer: sr.Recognizer | None = None,
        speaker=None,
        language: str | None = None,
        timeout: float | None = None,
        phrase_time_limit: float | None = None,
    ):
        self.recognizer = recognizer or sr.Recognizer()

        self.language = (
            language
            or os.getenv("SPEECH_LANGUAGE", "en-IN")
        )

        self.timeout = self._float_setting(
            timeout,
            "SPEECH_TIMEOUT",
            5.0,
        )

        self.phrase_time_limit = self._float_setting(
            phrase_time_limit,
            "SPEECH_PHRASE_TIME_LIMIT",
            10.0,
        )

        self._speaker = speaker
        self._speaker_lock = None

    # ------------------------------------------------------------------
    # Microphone
    # ------------------------------------------------------------------
    def check_microphone(self) -> bool:
        """
        Check whether the Windows default microphone can be opened.

        Returns True when available.
        """
        try:
            with sr.Microphone():
                return True

        except OSError as error:
            logger.warning(
                "Microphone unavailable: %s",
                error,
            )
            return False

        except Exception:
            logger.exception(
                "Unexpected microphone check failure."
            )
            return False

    def microphone_status(self) -> str:
        """Return a short user-facing microphone status."""
        try:
            with sr.Microphone():
                return "Microphone ready."

        except OSError as error:
            logger.warning(
                "Microphone status check failed: %s",
                error,
            )

            if "-9999" in str(error):
                return (
                    "Microphone unavailable. Check your Windows "
                    "default input device."
                )

            return (
                "Microphone unavailable. Check Windows microphone "
                "permissions and your default input device."
            )

        except Exception:
            logger.exception(
                "Unexpected microphone status failure."
            )
            return (
                "Microphone unavailable. Check Windows microphone "
                "settings."
            )

    # ------------------------------------------------------------------
    # Speech recognition
    # ------------------------------------------------------------------
    def listen(self) -> SpeechResult:
        """
        Listen once from the default microphone and convert speech to text.

        No audio is saved locally.
        """
        try:
            with sr.Microphone() as source:
                try:
                    self.recognizer.adjust_for_ambient_noise(
                        source,
                        duration=0.5,
                    )
                except Exception:
                    logger.warning(
                        "Could not adjust for ambient noise.",
                        exc_info=True,
                    )

                logger.info("Listening for speech.")

                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.timeout,
                        phrase_time_limit=self.phrase_time_limit,
                    )
                except sr.WaitTimeoutError:
                    logger.info("Speech listening timed out.")
                    return SpeechResult(
                        text="",
                        success=False,
                        error_code="timeout",
                    )

            logger.info("Speech captured. Sending for recognition.")

            try:
                text = self.recognizer.recognize_google(
                    audio,
                    language=self.language,
                )

            except sr.UnknownValueError:
                logger.info(
                    "Speech recognition could not understand the audio."
                )
                return SpeechResult(
                    text="",
                    success=False,
                    error_code="unintelligible",
                )

            except sr.RequestError as error:
                logger.warning(
                    "Speech recognition service unavailable: %s",
                    error,
                )
                return SpeechResult(
                    text="",
                    success=False,
                    error_code="service_unavailable",
                )

            cleaned = " ".join(str(text).split()).strip()

            if not cleaned:
                return SpeechResult(
                    text="",
                    success=False,
                    error_code="empty",
                )

            logger.info(
                "Speech recognized successfully."
            )

            return SpeechResult(
                text=cleaned,
                success=True,
            )

        except OSError as error:
            logger.warning(
                "Microphone could not be opened: %s",
                error,
            )

            if "-9999" in str(error):
                return SpeechResult(
                    text="",
                    success=False,
                    error_code="microphone_unavailable",
                )

            return SpeechResult(
                text="",
                success=False,
                error_code="microphone_error",
            )

        except Exception:
            logger.exception(
                "Unexpected speech-input failure."
            )
            return SpeechResult(
                text="",
                success=False,
                error_code="unexpected",
            )

    # ------------------------------------------------------------------
    # User-friendly messages
    # ------------------------------------------------------------------
    @staticmethod
    def error_message(error_code: str | None) -> str:
        """Convert an internal speech error code into UI-friendly text."""
        messages = {
            "timeout": "I didn't hear anything.",
            "unintelligible": "I could not understand what you said.",
            "service_unavailable": (
                "The speech service is unavailable right now."
            ),
            "microphone_unavailable": (
                "The microphone is unavailable. "
                "Please check your Windows default input device."
            ),
            "microphone_error": (
                "I couldn't access the microphone. "
                "Please check your Windows microphone settings."
            ),
            "empty": "I didn't receive any speech.",
            "unexpected": (
                "Something went wrong while listening."
            ),
        }

        return messages.get(
            error_code,
            "I couldn't process the microphone input.",
        )

    # ------------------------------------------------------------------
    # Text to speech
    # ------------------------------------------------------------------
    def _get_speaker(self):
        if self._speaker is None:
            logger.info("Initializing text-to-speech engine.")

            self._speaker = pyttsx3.init()

            # Optional voice configuration.
            rate = self._safe_int_env(
                "TTS_RATE",
                175,
            )

            volume = self._safe_float_env(
                "TTS_VOLUME",
                1.0,
            )

            try:
                self._speaker.setProperty(
                    "rate",
                    rate,
                )

                self._speaker.setProperty(
                    "volume",
                    max(0.0, min(1.0, volume)),
                )

            except Exception:
                logger.warning(
                    "Could not configure TTS properties.",
                    exc_info=True,
                )

        return self._speaker

    def speak(self, text: str) -> bool:
        """
        Speak text through the installed Windows TTS engine.

        Returns True on success and False on failure.
        """
        if not isinstance(text, str) or not text.strip():
            return False

        try:
            speaker = self._get_speaker()

            speaker.say(text.strip())
            speaker.runAndWait()

            logger.info("Spoke response successfully.")
            return True

        except Exception:
            logger.exception(
                "Text-to-speech failed."
            )
            return False

    def stop_speaking(self) -> bool:
        """Stop currently queued speech when supported by the engine."""
        if self._speaker is None:
            return True

        try:
            self._speaker.stop()
            return True

        except Exception:
            logger.exception(
                "Could not stop text-to-speech."
            )
            return False

    # ------------------------------------------------------------------
    # Small configuration helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _float_setting(
        explicit_value,
        environment_name: str,
        default: float,
    ) -> float:
        if explicit_value is not None:
            value = float(explicit_value)
        else:
            raw = os.getenv(environment_name)

            if raw is None:
                value = default
            else:
                try:
                    value = float(raw)
                except ValueError:
                    value = default

        if value <= 0:
            return default

        return value

    @staticmethod
    def _safe_int_env(
        environment_name: str,
        default: int,
    ) -> int:
        raw = os.getenv(environment_name)

        try:
            value = int(raw) if raw is not None else default
        except ValueError:
            value = default

        return max(1, value)

    @staticmethod
    def _safe_float_env(
        environment_name: str,
        default: float,
    ) -> float:
        raw = os.getenv(environment_name)

        try:
            value = float(raw) if raw is not None else default
        except ValueError:
            value = default

        return value


def listen_once() -> SpeechResult:
    """Convenience function for one microphone attempt."""
    return SpeechService().listen()


def speak_text(text: str) -> bool:
    """Convenience function for speaking one response."""
    return SpeechService().speak(text)
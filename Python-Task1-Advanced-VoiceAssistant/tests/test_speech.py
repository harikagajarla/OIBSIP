import speech_recognition as sr

from app.speech import (
    MicrophoneUnavailableError,
    SpeechResult,
    SpeechService,
    SpeechRecognitionError,
    SpeechServiceUnavailableError,
    SpeechTimeoutError,
)


class FakeMicrophone:
    """Fake microphone context manager for unit tests."""

    def __init__(self, error=None):
        self.error = error

    def __enter__(self):
        if self.error:
            raise self.error
        return object()

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeSpeaker:
    """Fake TTS engine."""

    def __init__(self):
        self.calls = []
        self.properties = {}
        self.stopped = False

    def say(self, text):
        self.calls.append(text)

    def runAndWait(self):
        return None

    def stop(self):
        self.stopped = True

    def setProperty(self, name, value):
        self.properties[name] = value


class FakeRecognizer:
    """Fake recognizer whose behavior can be controlled per test."""

    def __init__(
        self,
        recognized_text="hello",
        recognize_error=None,
        listen_error=None,
    ):
        self.recognized_text = recognized_text
        self.recognize_error = recognize_error
        self.listen_error = listen_error
        self.adjust_called = False
        self.listen_called = False

    def adjust_for_ambient_noise(self, source, duration=0.5):
        self.adjust_called = True

    def listen(
        self,
        source,
        timeout=5.0,
        phrase_time_limit=10.0,
    ):
        self.listen_called = True

        if self.listen_error:
            raise self.listen_error

        return "fake-audio"

    def recognize_google(self, audio, language="en-IN"):
        if self.recognize_error:
            raise self.recognize_error

        return self.recognized_text


# ------------------------------------------------------------------
# SpeechResult
# ------------------------------------------------------------------

def test_speech_result_success():
    result = SpeechResult(text="hello")

    assert result.success is True
    assert result.text == "hello"
    assert result.error_code is None


def test_speech_result_error():
    result = SpeechResult(
        text="",
        success=False,
        error_code="timeout",
    )

    assert result.success is False
    assert result.text == ""
    assert result.error_code == "timeout"


# ------------------------------------------------------------------
# Microphone
# ------------------------------------------------------------------

def test_microphone_check_success(monkeypatch):
    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(),
    )

    service = SpeechService()

    assert service.check_microphone() is True


def test_microphone_check_failure(monkeypatch):
    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(
            OSError("-9999 microphone host error")
        ),
    )

    service = SpeechService()

    assert service.check_microphone() is False


def test_microphone_status_ready(monkeypatch):
    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(),
    )

    service = SpeechService()

    assert service.microphone_status() == "Microphone ready."


def test_microphone_status_9999(monkeypatch):
    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(
            OSError("-9999 microphone host error")
        ),
    )

    service = SpeechService()

    message = service.microphone_status()

    assert "Microphone unavailable" in message
    assert "default input device" in message


# ------------------------------------------------------------------
# Speech recognition
# ------------------------------------------------------------------

def test_listen_success(monkeypatch):
    recognizer = FakeRecognizer(
        recognized_text="What is Python"
    )

    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(),
    )

    service = SpeechService(
        recognizer=recognizer,
    )

    result = service.listen()

    assert result.success is True
    assert result.text == "What is Python"
    assert result.error_code is None
    assert recognizer.adjust_called is True
    assert recognizer.listen_called is True


def test_listen_cleans_extra_spaces(monkeypatch):
    recognizer = FakeRecognizer(
        recognized_text="   hello    Harika   "
    )

    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(),
    )

    service = SpeechService(
        recognizer=recognizer,
    )

    result = service.listen()

    assert result.success is True
    assert result.text == "hello Harika"


def test_listen_timeout(monkeypatch):
    recognizer = FakeRecognizer(
        listen_error=sr.WaitTimeoutError()
    )

    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(),
    )

    service = SpeechService(
        recognizer=recognizer,
    )

    result = service.listen()

    assert result.success is False
    assert result.error_code == "timeout"
    assert result.text == ""


def test_listen_unintelligible(monkeypatch):
    recognizer = FakeRecognizer(
        recognize_error=sr.UnknownValueError()
    )

    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(),
    )

    service = SpeechService(
        recognizer=recognizer,
    )

    result = service.listen()

    assert result.success is False
    assert result.error_code == "unintelligible"


def test_listen_service_unavailable(monkeypatch):
    recognizer = FakeRecognizer(
        recognize_error=sr.RequestError("network unavailable")
    )

    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(),
    )

    service = SpeechService(
        recognizer=recognizer,
    )

    result = service.listen()

    assert result.success is False
    assert result.error_code == "service_unavailable"


def test_listen_microphone_unavailable(monkeypatch):
    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(
            OSError("-9999 microphone host error")
        ),
    )

    service = SpeechService()

    result = service.listen()

    assert result.success is False
    assert result.error_code == "microphone_unavailable"


def test_listen_general_microphone_error(monkeypatch):
    monkeypatch.setattr(
        sr,
        "Microphone",
        lambda: FakeMicrophone(
            OSError("device unavailable")
        ),
    )

    service = SpeechService()

    result = service.listen()

    assert result.success is False
    assert result.error_code == "microphone_error"


# ------------------------------------------------------------------
# Error messages
# ------------------------------------------------------------------

def test_timeout_error_message():
    message = SpeechService.error_message("timeout")

    assert message == "I didn't hear anything."


def test_unintelligible_error_message():
    message = SpeechService.error_message("unintelligible")

    assert "could not understand" in message.lower()


def test_service_error_message():
    message = SpeechService.error_message(
        "service_unavailable"
    )

    assert "speech service" in message.lower()


def test_microphone_error_message():
    message = SpeechService.error_message(
        "microphone_unavailable"
    )

    assert "microphone" in message.lower()


def test_unknown_error_message():
    message = SpeechService.error_message("something_unknown")

    assert message


# ------------------------------------------------------------------
# Text to speech
# ------------------------------------------------------------------

def test_speak_success(monkeypatch):
    speaker = FakeSpeaker()

    service = SpeechService(
        speaker=speaker,
    )

    result = service.speak(
        "Hello Harika"
    )

    assert result is True
    assert speaker.calls == ["Hello Harika"]


def test_speak_empty_text():
    speaker = FakeSpeaker()

    service = SpeechService(
        speaker=speaker,
    )

    assert service.speak("") is False
    assert speaker.calls == []


def test_speak_whitespace_text():
    speaker = FakeSpeaker()

    service = SpeechService(
        speaker=speaker,
    )

    assert service.speak("   ") is False
    assert speaker.calls == []


def test_stop_speaking():
    speaker = FakeSpeaker()

    service = SpeechService(
        speaker=speaker,
    )

    assert service.stop_speaking() is True
    assert speaker.stopped is True


def test_stop_speaking_without_engine():
    service = SpeechService()

    assert service.stop_speaking() is True


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

def test_custom_language():
    service = SpeechService(
        language="en-US",
    )

    assert service.language == "en-US"


def test_environment_language(monkeypatch):
    monkeypatch.setenv(
        "SPEECH_LANGUAGE",
        "en-GB",
    )

    service = SpeechService()

    assert service.language == "en-GB"


def test_environment_timeout(monkeypatch):
    monkeypatch.setenv(
        "SPEECH_TIMEOUT",
        "8",
    )

    service = SpeechService()

    assert service.timeout == 8.0


def test_invalid_environment_timeout_uses_default(monkeypatch):
    monkeypatch.setenv(
        "SPEECH_TIMEOUT",
        "invalid",
    )

    service = SpeechService()

    assert service.timeout == 5.0


def test_invalid_environment_phrase_limit_uses_default(monkeypatch):
    monkeypatch.setenv(
        "SPEECH_PHRASE_TIME_LIMIT",
        "invalid",
    )

    service = SpeechService()

    assert service.phrase_time_limit == 10.0


# ------------------------------------------------------------------
# TTS engine initialization
# ------------------------------------------------------------------

def test_speak_creates_engine(monkeypatch):
    speaker = FakeSpeaker()

    monkeypatch.setattr(
        "app.speech.pyttsx3.init",
        lambda: speaker,
    )

    service = SpeechService()

    assert service._speaker is None

    assert service.speak(
        "Testing speech"
    ) is True

    assert service._speaker is speaker
    assert speaker.calls == ["Testing speech"]


def test_speak_engine_failure(monkeypatch):
    class BrokenSpeaker:
        def say(self, text):
            raise RuntimeError("TTS failed")

        def runAndWait(self):
            pass

    service = SpeechService(
        speaker=BrokenSpeaker(),
    )

    assert service.speak(
        "Test"
    ) is False
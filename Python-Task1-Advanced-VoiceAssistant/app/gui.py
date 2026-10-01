"""CustomTkinter desktop interface for the Advanced Voice Assistant."""

from __future__ import annotations

import logging
import queue
import threading

import customtkinter as ctk

from app.commands import CommandExecutor
from app.database import Database
from app.intent import Intent, IntentName, detect
from app.knowledge_base import KnowledgeBase
from app.reminders import ReminderManager
from app.speech import SpeechService

logger = logging.getLogger(__name__)


class AssistantApp(ctk.CTk):
    """Main desktop window for text and voice interaction."""

    def __init__(self):
        super().__init__()

        self.title("Advanced Voice Assistant")
        self.geometry("900x650")
        self.minsize(760, 560)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --------------------------------------------------------------
        # Core services
        # --------------------------------------------------------------
        self.database = Database()
        self.database.initialize()

        self.knowledge_base = KnowledgeBase.default()
        self.reminder_manager = ReminderManager(
            database=self.database,
        )

        self.executor = CommandExecutor(
            database=self.database,
            reminder_manager=self.reminder_manager,
            knowledge_base=self.knowledge_base,
        )

        self.speech = SpeechService()

        self.listening = False
        self.processing = False
        self.closing = False

        self.reminder_scheduler = self.reminder_manager.start_scheduler(
            self._on_reminders_due,
            interval_seconds=2.0,
        )

        self.command_queue = queue.Queue()

        self.command_worker = threading.Thread(
            target=self._command_worker,
            daemon=True,
        )
        self.command_worker.start()

        self._build_ui()
        self._update_microphone_status()

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --------------------------------------------------------------
        # Header
        # --------------------------------------------------------------
        header = ctk.CTkFrame(
            self,
            corner_radius=0,
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=0,
            pady=0,
        )

        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Voice Assistant",
            font=ctk.CTkFont(
                size=25,
                weight="bold",
            ),
        )
        title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=24,
            pady=(18, 2),
        )

        # --------------------------------------------------------------
        # Conversation area
        # --------------------------------------------------------------
        chat_frame = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        chat_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=18,
            pady=(18, 10),
        )

        chat_frame.grid_rowconfigure(1, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)

        chat_title = ctk.CTkLabel(
            chat_frame,
            text="Conversation",
            font=ctk.CTkFont(
                size=17,
                weight="bold",
            ),
        )
        chat_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=16,
            pady=(14, 8),
        )

        self.chat_box = ctk.CTkTextbox(
            chat_frame,
            wrap="word",
            font=ctk.CTkFont(size=14),
        )
        self.chat_box.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 12),
        )

        self.chat_box.configure(
            state="disabled",
        )

        # --------------------------------------------------------------
        # Input section
        # --------------------------------------------------------------
        input_frame = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        input_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 10),
        )

        input_frame.grid_columnconfigure(0, weight=1)

        self.input_box = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a command, e.g. What is Python?",
            height=46,
            font=ctk.CTkFont(size=14),
        )
        self.input_box.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )

        self.send_button = ctk.CTkButton(
            input_frame,
            text="Send",
            width=90,
            height=46,
            command=self.on_send,
        )
        self.send_button.grid(
            row=0,
            column=1,
            padx=4,
        )

        self.listen_button = ctk.CTkButton(
            input_frame,
            text="🎤 Listen",
            width=110,
            height=46,
            command=self.on_listen,
        )
        self.listen_button.grid(
            row=0,
            column=2,
            padx=4,
        )

        self.stop_button = ctk.CTkButton(
            input_frame,
            text="Stop",
            width=80,
            height=46,
            command=self.stop_speaking,
        )
        self.stop_button.grid(
            row=0,
            column=3,
            padx=(4, 0),
        )

        self.input_box.bind(
            "<Return>",
            self._on_enter,
        )

        # --------------------------------------------------------------
        # Footer
        # --------------------------------------------------------------
        footer = ctk.CTkFrame(
            self,
            corner_radius=10,
        )
        footer.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 18),
        )

        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=0)
        footer.grid_columnconfigure(2, weight=0)

        self.status_label = ctk.CTkLabel(
            footer,
            text="Checking microphone...",
            anchor="w",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=10,
        )

        self.retry_button = ctk.CTkButton(
            footer,
            text="Retry microphone",
            width=130,
            height=30,
            command=self.retry_microphone,
        )
        self.retry_button.grid(
            row=0,
            column=1,
            padx=10,
            pady=7,
        )
        self.custom_command_button = ctk.CTkButton(
            footer,
            text="Custom Command",
            width=140,
            height=30,
            command=self._open_custom_command_form,
        )
        self.custom_command_button.grid(
            row=0,
            column=2,
            padx=(0, 10),
            pady=7,
        )

        self._append_system_message(
            "Assistant ready. You can type a command or click Listen."
        )

    # ==================================================================
    # Conversation helpers
    # ==================================================================

    def _append_message(self, speaker: str, text: str):
        """Safely append text to the conversation box."""

        if not text:
            return

        def update():
            self.chat_box.configure(
                state="normal",
            )

            self.chat_box.insert(
                "end",
                f"{speaker}: {text}\n\n",
            )

            self.chat_box.see(
                "end",
            )

            self.chat_box.configure(
                state="disabled",
            )

        self.after(
            0,
            update,
        )

    def _append_system_message(self, text: str):
        self._append_message(
            "Assistant",
            text,
        )
        # ==================================================================
    # Automatic reminder notifications
    # ==================================================================

    def _on_reminders_due(self, reminders):
        """Receive due reminders from the background scheduler."""

        if self.closing or not reminders:
            return

        self.after(
            0,
            self._show_due_reminders,
            reminders,
        )

    def _show_due_reminders(self, reminders):
        """Display and announce reminders that have reached their time."""

        if self.closing:
            return

        for reminder in reminders:
            message = (
                f"Reminder: {reminder.message}"
            )

            self._append_system_message(
                message,
            )

            threading.Thread(
                target=self._speak_reminder,
                args=(message,),
                daemon=True,
            ).start()

        self.status_label.configure(
            text=f"{len(reminders)} reminder(s) due.",
        )

        self.after(
            3000,
            self._update_microphone_status,
        )

    def _speak_reminder(self, message: str):
        """Speak one reminder without blocking the GUI."""

        try:
            self.speech.speak(
                message,
            )
        except Exception:
            logger.exception(
                "Reminder speech failed.",
            )
    
    # ==================================================================
    # Text commands
    # ==================================================================

    def on_send(self):
        text = self.input_box.get().strip()

        if not text:
            return

        self.input_box.delete(
            0,
            "end",
        )

        self._append_message(
            "You",
            text,
        )

        self._run_command_async(
            text,
        )

    def _on_enter(self, _event):
        self.on_send()
        return "break"

    # ==================================================================
    # Command pipeline
    # ==================================================================

    def _run_command_async(self, text: str):
        """Add a command to the FIFO queue for background processing."""

        text = text.strip()

        if not text:
            return

        if self.closing:
            return

        self.command_queue.put(text)

        self.processing = True

        self.status_label.configure(
            text="Processing...",
        )

        # Keep Send available so more commands can be queued.
        self.send_button.configure(
            state="normal",
        )

        # Do not start another microphone recording while commands are running.
        self.listen_button.configure(
            state="disabled",
        )

    def _command_worker(self):
        """Process queued commands sequentially in FIFO order."""

        while True:
            text = self.command_queue.get()

            try:
                if text is None:
                    return

                self._process_command(text)

            except Exception:
                logger.exception(
                    "Command worker failed.",
                )

                if not self.closing:
                    self.after(
                        0,
                        self._append_system_message,
                        "Something went wrong while processing that command.",
                    )

            finally:
                self.command_queue.task_done()

                if not self.closing:
                    self.after(
                        0,
                        self._command_finished,
                    )

    def _process_command(self, text: str):
        """Detect and execute one command."""

        try:
            intent = detect(
                text,
                knowledge_base=self.knowledge_base,
            )

            response = self.executor.execute(
                intent,
            )

            if response.action == "email_form":
                self.after(
                    0,
                    self._open_email_form,
                    response.data,
                )

                if response.text:
                    self.after(
                        0,
                        self._append_system_message,
                        response.text,
                    )

                return

            if response.text:
                self.after(
                    0,
                    self._append_system_message,
                    response.text,
                )

                try:
                    self.speech.speak(
                        response.text,
                    )
                except Exception:
                    logger.exception(
                        "Text-to-speech failed.",
                    )

        except Exception:
            logger.exception(
                "Command processing failed.",
            )

            self.after(
                0,
                self._append_system_message,
                "I could not process that command. You can try again.",
            )

    def _command_finished(self):
        """Update the GUI after one command completes."""

        if self.closing:
            return

        # If another command is already waiting, stay in processing mode.
        if not self.command_queue.empty():
            self.processing = True

            self.status_label.configure(
                text="Processing queued command...",
            )

            return

        self.processing = False

        self.send_button.configure(
            state="normal",
        )

        self.listen_button.configure(
            text="🎤 Listen",
            state="normal",
        )

        self._update_microphone_status()


    # ==================================================================
    # Voice input
    # ==================================================================

    def on_listen(self):
        if self.listening:
            return

        self.listening = True

        self.listen_button.configure(
            text="Listening...",
            state="disabled",
        )

        self.send_button.configure(
            state="disabled",
        )

        self.status_label.configure(
            text="Listening... Speak now.",
        )

        worker = threading.Thread(
            target=self._listen_worker,
            daemon=True,
        )

        worker.start()

    def _listen_worker(self):
        try:
            result = self.speech.listen()

            if result.success and result.text:
                self._append_message(
                    "You",
                    result.text,
                )

                # Hand the recognized text back to Tkinter's main thread.
                self.after(
                    0,
                    lambda text=result.text: self._run_command_async(text),
                )
            else:
                message = self.speech.error_message(
                    result.error_code,
                )

                self._append_system_message(
                    message,
                )

        except Exception:
            logger.exception(
                "Voice input failed.",
            )

            self._append_system_message(
                "Voice input is unavailable right now. You can still type commands."
            )

        finally:
            self.after(
                0,
                self._listen_finished,
            )

    def _listen_finished(self):
        self.listening = False

        self.listen_button.configure(
            text="🎤 Listen",
            state="normal",
        )

        # Typing is available again after microphone capture.
        self.send_button.configure(
            state="normal",
        )

        if self.processing:
            self.listen_button.configure(
                text="🎤 Listen",
                state="disabled",
            )

        self._update_microphone_status()

    # ==================================================================
    # Email form
    # ==================================================================

    def _open_email_form(self, data=None):
        """Open a form for entering recipient, subject, and message."""

        data = data or {}

        window = ctk.CTkToplevel(self)
        window.title("Send Email")
        window.geometry("520x650")
        window.minsize(480, 460)
        window.transient(self)
        window.grab_set()

        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(6, weight=1)

        title = ctk.CTkLabel(
            window,
            text="Send Email",
            font=ctk.CTkFont(
                size=22,
                weight="bold",
            ),
        )
        title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=24,
            pady=(24, 16),
        )

        recipient_label = ctk.CTkLabel(
            window,
            text="Recipient Email",
            anchor="w",
        )
        recipient_label.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=24,
            pady=(4, 4),
        )

        recipient_entry = ctk.CTkEntry(
            window,
            height=40,
            placeholder_text="example@gmail.com",
        )
        recipient_entry.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 12),
        )

        recipient_entry.insert(
            0,
            data.get("recipient", ""),
        )

        subject_label = ctk.CTkLabel(
            window,
            text="Subject",
            anchor="w",
        )
        subject_label.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=24,
            pady=(4, 4),
        )

        subject_entry = ctk.CTkEntry(
            window,
            height=40,
            placeholder_text="Email subject",
        )
        subject_entry.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 12),
        )

        subject_entry.insert(
            0,
            data.get("subject", ""),
        )

        message_label = ctk.CTkLabel(
            window,
            text="Message",
            anchor="w",
        )
        message_label.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=24,
            pady=(4, 4),
        )

        message_box = ctk.CTkTextbox(
            window,
            height=170,
        )
        message_box.grid(
            row=6,
            column=0,
            sticky="nsew",
            padx=24,
            pady=(0, 16),
        )

        message_box.insert(
            "1.0",
            data.get("message", ""),
        )

        status_label = ctk.CTkLabel(
            window,
            text="",
            anchor="w",
        )
        status_label.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 8),
        )

        button_frame = ctk.CTkFrame(
            window,
            fg_color="transparent",
        )
        button_frame.grid(
            row=8,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 24),
        )

        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        send_button = ctk.CTkButton(
            button_frame,
            text="Send Email",
            height=42,
        )
        send_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            height=42,
            command=window.destroy,
        )
        cancel_button.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(6, 0),
        )

        def submit_email():
            recipient = recipient_entry.get().strip()
            subject = subject_entry.get().strip()
            message = message_box.get("1.0", "end").strip()

            if not recipient or not subject or not message:
                status_label.configure(
                    text="Please fill in all fields.",
                )
                return

            send_button.configure(
                state="disabled",
                text="Sending...",
            )

            status_label.configure(
                text="Sending email...",
            )

            intent = Intent(
                name=IntentName.SEND_EMAIL,
                confidence=1.0,
                entities={
                    "recipient": recipient,
                    "subject": subject,
                    "message": message,
                },
                raw_text="send email",
            )

            threading.Thread(
                target=send_email_worker,
                args=(intent,),
                daemon=True,
            ).start()

        def send_email_worker(intent):
            try:
                response = self.executor.execute(
                    intent,
                )

                self.after(
                    0,
                    finish_email,
                    response,
                )

            except Exception:
                logger.exception(
                    "Email form processing failed.",
                )

                self.after(
                    0,
                    finish_email,
                    None,
                )

        def finish_email(response):
            if response is None:
                status_label.configure(
                    text="Could not send the email.",
                )

                send_button.configure(
                    state="normal",
                    text="Send Email",
                )

                return

            self._append_system_message(
                response.text,
            )

            if response.success:
                status_label.configure(
                    text="Email sent successfully.",
                )

                try:
                    self.speech.speak(
                        response.text,
                    )
                except Exception:
                    logger.exception(
                        "Email success speech failed.",
                    )

                send_button.configure(
                    state="disabled",
                    text="Sent",
                )

                window.after(
                    1200,
                    window.destroy,
                )

            else:
                status_label.configure(
                    text=response.text,
                )

                send_button.configure(
                    state="normal",
                    text="Send Email",
                )

        send_button.configure(
            command=submit_email,
        )

        recipient_entry.focus_set()

    # ==================================================================
    # Custom command form
    # ==================================================================

    def _open_custom_command_form(self):
        """Open a form for creating a safe custom command."""

        window = ctk.CTkToplevel(self)
        window.title("Create Custom Command")
        window.geometry("540x450")
        window.minsize(500, 420)
        window.transient(self)
        window.grab_set()

        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(6, weight=1)

        title = ctk.CTkLabel(
            window,
            text="Create Custom Command",
            font=ctk.CTkFont(
                size=22,
                weight="bold",
            ),
        )
        title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=24,
            pady=(24, 8),
        )

        info = ctk.CTkLabel(
            window,
            text=(
                "Save a spoken shortcut for an action the assistant already supports."
            ),
            anchor="w",
            wraplength=480,
        )
        info.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 18),
        )

        name_label = ctk.CTkLabel(
            window,
            text="Command Name",
            anchor="w",
        )
        name_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 4),
        )

        name_entry = ctk.CTkEntry(
            window,
            height=40,
            placeholder_text="Example: work mode",
        )
        name_entry.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 14),
        )

        action_label = ctk.CTkLabel(
            window,
            text="Action",
            anchor="w",
        )
        action_label.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 4),
        )

        action_entry = ctk.CTkEntry(
            window,
            height=40,
            placeholder_text="Example: open vscode",
        )
        action_entry.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 14),
        )

        examples = ctk.CTkLabel(
            window,
            text=(
                "Examples: open vscode | open calculator | what is python | "
                "what is SQL"
            ),
            anchor="w",
            wraplength=480,
        )
        examples.grid(
            row=6,
            column=0,
            sticky="new",
            padx=24,
            pady=(0, 12),
        )

        status_label = ctk.CTkLabel(
            window,
            text="",
            anchor="w",
            wraplength=480,
        )
        status_label.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 8),
        )

        button_frame = ctk.CTkFrame(
            window,
            fg_color="transparent",
        )
        button_frame.grid(
            row=8,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 24),
        )

        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        save_button = ctk.CTkButton(
            button_frame,
            text="Save Command",
            height=42,
        )
        save_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            height=42,
            command=window.destroy,
        )
        cancel_button.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(6, 0),
        )

        def save_command():
            command_name = name_entry.get().strip()
            action = action_entry.get().strip()

            if not command_name or not action:
                status_label.configure(
                    text="Please enter both the command name and action.",
                )
                return

            if len(command_name) > 80:
                status_label.configure(
                    text="Command name is too long.",
                )
                return

            if len(action) > 500:
                status_label.configure(
                    text="Action is too long.",
                )
                return

            # Validate the action before storing it.
            try:
                action_intent = detect(
                    action,
                    knowledge_base=self.knowledge_base,
                )

                if action_intent.is_unknown:
                    status_label.configure(
                        text=(
                            "That action is not supported. Use a normal "
                            "assistant command such as 'open vscode' or "
                            "'what is python'."
                        ),
                    )
                    return

            except Exception:
                logger.exception(
                    "Custom command validation failed.",
                )

                status_label.configure(
                    text="Could not validate that action.",
                )
                return

            try:
                custom = self.database.add_custom_command(
                    command_name,
                    action,
                )

            except ValueError as error:
                status_label.configure(
                    text=str(error),
                )
                return

            except Exception:
                logger.exception(
                    "Could not save custom command.",
                )

                status_label.configure(
                    text="Could not save the custom command.",
                )
                return

            message = (
                f"Custom command '{custom.command_name}' saved. "
                f"Say 'run my {custom.command_name}' to use it."
            )

            self._append_system_message(
                message,
            )

            status_label.configure(
                text="Command saved successfully.",
            )

            try:
                self.speech.speak(
                    message,
                )
            except Exception:
                logger.exception(
                    "Custom command success speech failed.",
                )

            save_button.configure(
                state="disabled",
                text="Saved",
            )

            window.after(
                1200,
                window.destroy,
            )

        save_button.configure(
            command=save_command,
        )

        name_entry.focus_set()

    # ==================================================================
    # Microphone status
    # ==================================================================

    def _update_microphone_status(self):
        status = self.speech.microphone_status()

        self.status_label.configure(
            text=status,
        )

    def retry_microphone(self):
        self.status_label.configure(
            text="Checking microphone...",
        )

        self.after(
            50,
            self._update_microphone_status,
        )

    # ==================================================================
    # TTS controls
    # ==================================================================

    def stop_speaking(self):
        try:
            self.speech.stop_speaking()
        except Exception:
            logger.exception(
                "Could not stop speech.",
            )

    # ==================================================================
    # Shutdown
    # ==================================================================
    def close(self):
        self.closing = True

        try:
            self.reminder_scheduler.stop()
        except Exception:
            logger.exception(
                "Reminder scheduler shutdown failed.",
            )

        try:
            self.speech.stop_speaking()
        except Exception:
            logger.exception(
                "Speech shutdown failed.",
            )

        self.command_queue.put(None)

        self.destroy()

def main():
    app = AssistantApp()
    app.mainloop()


if __name__ == "__main__":
    main()
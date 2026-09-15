"""
app.py

Tkinter GUI for the Secure Password Generator.

This is the ONLY file that knows about Tkinter. It is responsible for:
    - Drawing the window and widgets.
    - Reading the user's chosen settings.
    - Calling into `password_generator` and `strength_checker` for the
      actual logic (this file contains no password-generation logic
      itself).
    - Displaying the result, strength, and validation/error messages.
    - Managing the in-memory session history (last 5 passwords).
    - Copying the password to the clipboard via `pyperclip`.

Security note:
    The session history list below lives only in this running process's
    memory (a plain Python list). It is never written to a file, never
    written to a database, and is destroyed the moment the application
    closes. Restarting the app always starts with an empty history.
"""

from __future__ import annotations

import tkinter as tk

try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except ImportError:
    # If pyperclip somehow isn't installed, the app should still run --
    # it just disables the clipboard feature and tells the user why.
    _PYPERCLIP_AVAILABLE = False

from password_generator import PasswordOptions, PasswordGeneratorError, generate_password
from strength_checker import calculate_strength


MAX_HISTORY_ENTRIES = 5
DEFAULT_LENGTH = 16
MIN_LENGTH = 8
MAX_LENGTH = 128

# Simple color palette used throughout the UI for consistency.
COLOR_BG = "#1e1e2e"
COLOR_PANEL = "#2a2a3d"
COLOR_TEXT = "#f2f2f2"
COLOR_MUTED = "#a0a0b8"
COLOR_ACCENT = "#5865f2"
COLOR_SUCCESS = "#3fb950"
COLOR_WARNING = "#e3b341"
COLOR_DANGER = "#f85149"

STRENGTH_COLORS = {
    "Weak": COLOR_DANGER,
    "Medium": COLOR_WARNING,
    "Strong": COLOR_SUCCESS,
}


class PasswordGeneratorApp:
    """The main application window and all of its behavior."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Secure Password Generator")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)

        # In-memory-only session history. This list is never saved to
        # disk. It disappears the moment the app process ends.
        self.session_history: list[str] = []
        self.history_visible = False

        # Tkinter variables bound to widgets.
        self.length_var = tk.IntVar(value=DEFAULT_LENGTH)
        self.upper_var = tk.BooleanVar(value=True)
        self.lower_var = tk.BooleanVar(value=True)
        self.digits_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.exclude_ambiguous_var = tk.BooleanVar(value=False)
        self.password_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        container = tk.Frame(self.root, bg=COLOR_BG, padx=24, pady=20)
        container.grid(row=0, column=0)

        self._build_title(container)
        self._build_length_section(container)
        self._build_character_section(container)
        self._build_generate_button(container)
        self._build_password_output_section(container)
        self._build_history_section(container)
        self._build_status_bar(container)

    def _build_title(self, parent: tk.Frame) -> None:
        title = tk.Label(
            parent,
            text="🔒 SECURE PASSWORD GENERATOR",
            font=("Segoe UI", 16, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_BG,
        )
        title.grid(row=0, column=0, columnspan=2, pady=(0, 4), sticky="w")

        subtitle = tk.Label(
            parent,
            text="Generate strong, secure passwords using Python's `secrets` module.",
            font=("Segoe UI", 9),
            fg=COLOR_MUTED,
            bg=COLOR_BG,
        )
        subtitle.grid(row=1, column=0, columnspan=2, pady=(0, 16), sticky="w")

    def _build_length_section(self, parent: tk.Frame) -> None:
        section = tk.LabelFrame(
            parent,
            text="Password Length",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            padx=12,
            pady=10,
            bd=0,
        )
        section.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        section.grid_columnconfigure(0, weight=1)

        # A Scale (slider) gives quick visual control...
        self.length_scale = tk.Scale(
            section,
            from_=MIN_LENGTH,
            to=MAX_LENGTH,
            orient="horizontal",
            variable=self.length_var,
            bg=COLOR_PANEL,
            fg=COLOR_TEXT,
            highlightthickness=0,
            troughcolor=COLOR_BG,
            activebackground=COLOR_ACCENT,
            length=280,
        )
        self.length_scale.grid(row=0, column=0, sticky="ew")

        # ...and a Spinbox gives precise numeric entry. Both are bound to
        # the same IntVar, so they always stay in sync with each other.
        self.length_spinbox = tk.Spinbox(
            section,
            from_=MIN_LENGTH,
            to=MAX_LENGTH,
            textvariable=self.length_var,
            width=5,
            justify="center",
            font=("Segoe UI", 10),
        )
        self.length_spinbox.grid(row=0, column=1, padx=(12, 0))

    def _build_character_section(self, parent: tk.Frame) -> None:
        section = tk.LabelFrame(
            parent,
            text="Character Types",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            padx=12,
            pady=10,
            bd=0,
        )
        section.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        checkbox_style = dict(
            bg=COLOR_PANEL,
            fg=COLOR_TEXT,
            selectcolor=COLOR_BG,
            activebackground=COLOR_PANEL,
            activeforeground=COLOR_TEXT,
            font=("Segoe UI", 10),
            anchor="w",
        )

        upper_cb = tk.Checkbutton(
            section, text="Uppercase (A-Z)", variable=self.upper_var, **checkbox_style
        )
        upper_cb.grid(row=0, column=0, sticky="w", padx=(0, 20))

        lower_cb = tk.Checkbutton(
            section, text="Lowercase (a-z)", variable=self.lower_var, **checkbox_style
        )
        lower_cb.grid(row=0, column=1, sticky="w")

        digits_cb = tk.Checkbutton(
            section, text="Numbers (0-9)", variable=self.digits_var, **checkbox_style
        )
        digits_cb.grid(row=1, column=0, sticky="w", padx=(0, 20), pady=(4, 0))

        symbols_cb = tk.Checkbutton(
            section, text="Symbols (!@#$...)", variable=self.symbols_var, **checkbox_style
        )
        symbols_cb.grid(row=1, column=1, sticky="w", pady=(4, 0))
        tk.Checkbutton(
            section,
            text="Exclude ambiguous characters (0, O, l, 1, I)",
            variable=self.exclude_ambiguous_var,
            **checkbox_style,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_generate_button(self, parent: tk.Frame) -> None:
        generate_btn = tk.Button(
            parent,
            text="Generate Password",
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_ACCENT,
            fg="white",
            activebackground="#4752c4",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=8,
            cursor="hand2",
            command=self.on_generate_clicked,
        )
        generate_btn.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 16))

    def _build_password_output_section(self, parent: tk.Frame) -> None:
        section = tk.LabelFrame(
            parent,
            text="Generated Password",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            padx=12,
            pady=10,
            bd=0,
        )
        section.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        section.grid_columnconfigure(0, weight=1)

        self.password_entry = tk.Entry(
            section,
            textvariable=self.password_var,
            font=("Consolas", 13),
            state="readonly",
            readonlybackground=COLOR_BG,
            fg=COLOR_SUCCESS,
            justify="center",
            relief="flat",
        )
        self.password_entry.grid(row=0, column=0, sticky="ew", ipady=6)

        self.copy_button = tk.Button(
            section,
            text="Copy to Clipboard",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            relief="flat",
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.on_copy_clicked,
        )
        self.copy_button.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        strength_row = tk.Frame(section, bg=COLOR_PANEL)
        strength_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        strength_caption = tk.Label(
            strength_row,
            text="Strength:",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
        )
        strength_caption.pack(side="left")

        self.strength_label = tk.Label(
            strength_row,
            text="—",
            font=("Segoe UI", 9, "bold"),
            fg=COLOR_MUTED,
            bg=COLOR_PANEL,
        )
        self.strength_label.pack(side="left", padx=(6, 0))

    def _build_history_section(self, parent: tk.Frame) -> None:
        section = tk.LabelFrame(
            parent,
            text="Recent Session Passwords (this session only — never saved to disk)",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_TEXT,
            bg=COLOR_PANEL,
            padx=12,
            pady=10,
            bd=0,
        )
        section.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        section.grid_columnconfigure(0, weight=1)

        self.toggle_history_btn = tk.Button(
            section,
            text="Show History",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            relief="flat",
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.on_toggle_history_clicked,
        )
        self.toggle_history_btn.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.history_labels: list[tk.Label] = []
        for i in range(MAX_HISTORY_ENTRIES):
            lbl = tk.Label(
                section,
                text=f"{i + 1}. ---",
                font=("Consolas", 9),
                fg=COLOR_MUTED,
                bg=COLOR_PANEL,
                anchor="w",
            )
            lbl.grid(row=i + 1, column=0, sticky="ew")
            self.history_labels.append(lbl)

    def _build_status_bar(self, parent: tk.Frame) -> None:
        self.status_label = tk.Label(
            parent,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg=COLOR_MUTED,
            bg=COLOR_BG,
            anchor="w",
            wraplength=360,
            justify="left",
        )
        self.status_label.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def on_generate_clicked(self) -> None:
        """
        Handle a click on "Generate Password".

        Reads the current widget state, asks password_generator to do
        the real work, and updates the UI. All expected failure modes
        (bad length, too few categories, etc.) raise PasswordGeneratorError,
        which we catch here and show as a friendly status message --
        the user never sees a raw Python traceback.
        """
        options = PasswordOptions(
            length=self.length_var.get(),
            use_upper=self.upper_var.get(),
            use_lower=self.lower_var.get(),
            use_digits=self.digits_var.get(),
            use_symbols=self.symbols_var.get(),
            exclude_ambiguous=self.exclude_ambiguous_var.get(),
        )

        try:
            password = generate_password(options)
        except PasswordGeneratorError as error:
            # Expected, user-facing validation problem.
            self._show_status(str(error), is_error=True)
            self.password_var.set("")
            self.strength_label.config(text="—", fg=COLOR_MUTED)
            return
        except Exception as unexpected_error:
            # Something we did not anticipate. We still refuse to show a
            # raw traceback to the user, but we log a generic message.
            # (During development, print the real error to the console
            # so it can be debugged -- this print never includes the
            # generated password itself.)
            print(f"[DEBUG] Unexpected error during generation: {unexpected_error!r}")
            self._show_status(
                "Something went wrong while generating the password. Please try again.",
                is_error=True,
            )
            return

        self.password_var.set(password)
        self._update_strength_display(password)
        self._add_to_history(password)
        self._auto_copy_to_clipboard(password)
        self._show_status("Password generated successfully.", is_error=False)

    def on_copy_clicked(self) -> None:
        """Handle a manual click on 'Copy to Clipboard'."""
        password = self.password_var.get()
        if not password:
            self._show_status("Generate a password first.", is_error=True)
            return
        self._copy_to_clipboard(password, manual=True)

    def on_toggle_history_clicked(self) -> None:
        """
        Toggle whether the session history passwords are shown in full
        or masked. This is a small security-minded UI touch: the
        internship requirement is to DISPLAY the last 5 passwords, but
        we default to a masked view so a generated password isn't left
        visible on-screen (e.g. during a demo or screenshot) unless the
        user deliberately chooses to reveal it.
        """
        self.history_visible = not self.history_visible
        self.toggle_history_btn.config(
            text="Hide History" if self.history_visible else "Show History"
        )
        self._refresh_history_labels()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _update_strength_display(self, password: str) -> None:
        strength = calculate_strength(password)
        color = STRENGTH_COLORS.get(strength, COLOR_MUTED)
        self.strength_label.config(text=strength, fg=color)

    def _add_to_history(self, password: str) -> None:
        """
        Add a password to the in-memory session history, keeping only
        the most recent MAX_HISTORY_ENTRIES. This list is never written
        to a file or database, so it is lost as soon as the app closes.
        """
        self.session_history.insert(0, password)
        del self.session_history[MAX_HISTORY_ENTRIES:]
        self._refresh_history_labels()

    def _refresh_history_labels(self) -> None:
        for i, label in enumerate(self.history_labels):
            if i < len(self.session_history):
                entry = self.session_history[i]
                display_text = entry if self.history_visible else self._mask(entry)
                label.config(text=f"{i + 1}. {display_text}", fg=COLOR_TEXT)
            else:
                label.config(text=f"{i + 1}. ---", fg=COLOR_MUTED)

    @staticmethod
    def _mask(password: str) -> str:
        """Return a masked version of a password, e.g. 'Ab3•••••z9'."""
        if len(password) <= 4:
            return "•" * len(password)
        return password[:2] + "•" * (len(password) - 4) + password[-2:]

    def _auto_copy_to_clipboard(self, password: str) -> None:
        """Automatically copy a freshly generated password to the clipboard."""
        self._copy_to_clipboard(password, manual=False)

    def _copy_to_clipboard(self, password: str, manual: bool) -> None:
        if not _PYPERCLIP_AVAILABLE:
            self._show_status(
                "Clipboard feature unavailable: the 'pyperclip' package is not installed.",
                is_error=True,
            )
            return
        try:
            pyperclip.copy(password)
        except Exception as clipboard_error:
            print(f"[DEBUG] Clipboard error: {clipboard_error!r}")
            self._show_status(
                "Could not copy to clipboard on this system. You can still select "
                "and copy the password manually.",
                is_error=True,
            )
            return

        if manual:
            self._show_status("Password copied to clipboard.", is_error=False)
        else:
            self._show_status("Password generated and copied to clipboard.", is_error=False)

    def _show_status(self, message: str, is_error: bool) -> None:
        self.status_var.set(message)
        self.status_label.config(fg=COLOR_DANGER if is_error else COLOR_SUCCESS)


def main() -> None:
    """Entry point: create the Tk root window and run the app."""
    root = tk.Tk()
    PasswordGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

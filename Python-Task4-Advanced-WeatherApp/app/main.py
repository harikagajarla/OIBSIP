"""
App entry point orchestration.

Checks the API key is configured before opening any window, so
failures are reported with a clear message rather than a crash deep
inside a network call.
"""

import sys
import tkinter.messagebox as messagebox

from app import config


def run() -> None:
    try:
        config.ensure_api_key_present()
    except config.MissingAPIKeyError as exc:
        # Show a message box even though the main window hasn't opened yet.
        messagebox.showerror("Configuration Error", str(exc))
        sys.exit(1)

    # Import UI only after the key check passes (avoids building the
    # whole widget tree just to fail immediately after).
    from app.ui import WeatherApp

    app = WeatherApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

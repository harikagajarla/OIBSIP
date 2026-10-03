"""Entry point: launches the BMI Tracker GUI."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

from bmi_tracker.exceptions import DatabaseError
from bmi_tracker.services.tracker_service import TrackerService
from bmi_tracker.ui.main_window import MainWindow


def main() -> int:
    try:
        service = TrackerService()
    except DatabaseError as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("BMI Tracker - database error", str(error))
        root.destroy()
        return 1

    MainWindow(service).mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

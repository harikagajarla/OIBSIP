"""Main tkinter window: user selection, BMI input, colour-coded result, history."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from bmi_tracker import config
from bmi_tracker.db.database import Record, User
from bmi_tracker.exceptions import DatabaseError, ValidationError
from bmi_tracker.services.tracker_service import TrackerService
from bmi_tracker.ui.trend_view import TrendWindow

_NEUTRAL_TEXT = "#222222"
_ERROR_TEXT = "#C62828"


class MainWindow(tk.Tk):
    """The application window. It only collects input and shows results;
    all logic lives in the service layer."""

    def __init__(self, service: TrackerService) -> None:
        super().__init__()
        self._service = service
        self._users: list[User] = []

        self.title(config.APP_TITLE)
        self.geometry("720x700")
        self.minsize(660, 620)

        self.user_var = tk.StringVar()
        self.new_user_var = tk.StringVar()
        self.weight_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.error_var = tk.StringVar()
        self.bmi_var = tk.StringVar(value="BMI: --")
        self.category_var = tk.StringVar(value="Category: --")

        self._build_widgets()
        self._load_users()

    # ------------------------------------------------------------ layout
    def _build_widgets(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        ttk.Label(container, text="BMI Calculator & Tracker", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )
        self._build_user_section(container).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._build_input_section(container).grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self._build_result_section(container).grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self._build_history_section(container).grid(row=4, column=0, sticky="nsew")

    def _build_user_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="User", padding=10)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Select user:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.user_combo = ttk.Combobox(frame, textvariable=self.user_var, state="readonly")
        self.user_combo.grid(row=0, column=1, columnspan=2, sticky="ew", pady=4)
        self.user_combo.bind("<<ComboboxSelected>>", self._on_user_selected)

        ttk.Label(frame, text="New user name:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        new_user_entry = ttk.Entry(frame, textvariable=self.new_user_var)
        new_user_entry.grid(row=1, column=1, sticky="ew", pady=4)
        new_user_entry.bind("<Return>", lambda _event: self._on_add_user())
        ttk.Button(frame, text="Add User", command=self._on_add_user).grid(
            row=1, column=2, padx=(8, 0), pady=4
        )
        return frame

    def _build_input_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="Measurements", padding=10)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Weight (kg):").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        weight_entry = ttk.Entry(frame, textvariable=self.weight_var)
        weight_entry.grid(row=0, column=1, sticky="ew", pady=4)
        weight_entry.bind("<Return>", lambda _event: self._on_calculate())

        ttk.Label(frame, text="Height (m):").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        height_entry = ttk.Entry(frame, textvariable=self.height_var)
        height_entry.grid(row=1, column=1, sticky="ew", pady=4)
        height_entry.bind("<Return>", lambda _event: self._on_calculate())

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 4))
        ttk.Button(buttons, text="Calculate BMI", command=self._on_calculate).pack(side=tk.LEFT)
        ttk.Button(buttons, text="View Trend Graph", command=self._on_show_trend).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        ttk.Label(
            frame, textvariable=self.error_var, foreground=_ERROR_TEXT, wraplength=620, justify="left"
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        return frame

    def _build_result_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="Result (saved to the selected user's history)", padding=10)

        self.bmi_label = ttk.Label(
            frame, textvariable=self.bmi_var, font=("Segoe UI", 22, "bold"), foreground=_NEUTRAL_TEXT
        )
        self.bmi_label.pack(anchor="w")
        self.category_label = ttk.Label(
            frame, textvariable=self.category_var, font=("Segoe UI", 14), foreground=_NEUTRAL_TEXT
        )
        self.category_label.pack(anchor="w", pady=(0, 8))

        legend = ttk.Frame(frame)
        legend.pack(anchor="w")
        for name, colour in config.CATEGORY_COLOURS.items():
            tk.Label(
                legend,
                text=f"{name} ({config.CATEGORY_RANGES[name]})",
                bg=colour,
                fg="white",
                padx=8,
                pady=2,
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=(0, 6))
        return frame

    def _build_history_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="History (newest first)", padding=10)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("date", "weight", "height", "bmi", "category")
        headings = {
            "date": "Date & time",
            "weight": "Weight (kg)",
            "height": "Height (m)",
            "bmi": "BMI",
            "category": "Category",
        }
        self.history_tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        for column in columns:
            self.history_tree.heading(column, text=headings[column])
            self.history_tree.column(column, anchor="center", width=110)
        self.history_tree.column("date", width=150)
        for category, colour in config.CATEGORY_COLOURS.items():
            self.history_tree.tag_configure(category, foreground=colour)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        return frame

    # ---------------------------------------------------------- helpers
    def _selected_user(self) -> User | None:
        index = self.user_combo.current()
        if index < 0 or index >= len(self._users):
            return None
        return self._users[index]

    def _show_database_error(self, error: DatabaseError) -> None:
        messagebox.showerror(
            "Database error",
            f"{error}\n\nPlease check that the 'data' folder is writable and that the "
            "database file is not open in another program.",
            parent=self,
        )

    def _reset_result(self) -> None:
        self.bmi_var.set("BMI: --")
        self.category_var.set("Category: --")
        self.bmi_label.configure(foreground=_NEUTRAL_TEXT)
        self.category_label.configure(foreground=_NEUTRAL_TEXT)

    def _show_result(self, record: Record) -> None:
        colour = config.CATEGORY_COLOURS.get(record.category, _NEUTRAL_TEXT)
        self.bmi_var.set(f"BMI: {record.bmi:.2f}")
        self.category_var.set(f"Category: {record.category}")
        self.bmi_label.configure(foreground=colour)
        self.category_label.configure(foreground=colour)

    def _clear_history(self) -> None:
        self.history_tree.delete(*self.history_tree.get_children())

    def _load_users(self, select_user_id: int | None = None) -> None:
        try:
            self._users = self._service.list_users()
        except DatabaseError as error:
            self._show_database_error(error)
            return

        self.user_combo["values"] = [user.name for user in self._users]
        if not self._users:
            self.user_var.set("")
            self._clear_history()
            return

        index = 0
        if select_user_id is not None:
            for position, user in enumerate(self._users):
                if user.id == select_user_id:
                    index = position
                    break
        self.user_combo.current(index)
        self._refresh_history()

    def _refresh_history(self) -> None:
        self._clear_history()
        user = self._selected_user()
        if user is None:
            return
        try:
            records = self._service.get_history(user.id)
        except DatabaseError as error:
            self._show_database_error(error)
            return
        for record in reversed(records):
            self.history_tree.insert(
                "",
                tk.END,
                values=(
                    record.recorded_at.strftime("%Y-%m-%d %H:%M"),
                    f"{record.weight_kg:.1f}",
                    f"{record.height_m:.2f}",
                    f"{record.bmi:.2f}",
                    record.category,
                ),
                tags=(record.category,),
            )

    # ---------------------------------------------------------- handlers
    def _on_user_selected(self, _event: object = None) -> None:
        self.error_var.set("")
        self._reset_result()
        self._refresh_history()

    def _on_add_user(self) -> None:
        try:
            user = self._service.create_user(self.new_user_var.get())
        except ValidationError as error:
            self.error_var.set(str(error))
            return
        except DatabaseError as error:
            self._show_database_error(error)
            return
        self.new_user_var.set("")
        self.error_var.set("")
        self._reset_result()
        self._load_users(select_user_id=user.id)

    def _on_calculate(self) -> None:
        user = self._selected_user()
        if user is None:
            self.error_var.set("Please select a user (or add a new one) before calculating.")
            return
        try:
            record = self._service.calculate_and_save(
                user.id, self.weight_var.get(), self.height_var.get()
            )
        except ValidationError as error:
            self.error_var.set(str(error))
            return
        except DatabaseError as error:
            self._show_database_error(error)
            return
        self.error_var.set("")
        self._show_result(record)
        self._refresh_history()

    def _on_show_trend(self) -> None:
        user = self._selected_user()
        if user is None:
            self.error_var.set("Please select a user to view their trend graph.")
            return
        try:
            dates, values = self._service.get_trend_data(user.id)
        except DatabaseError as error:
            self._show_database_error(error)
            return
        self.error_var.set("")
        TrendWindow(self, user.name, dates, values)

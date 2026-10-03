"""tkinter window that displays the BMI trend graph."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Sequence

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from bmi_tracker.ui.trend_chart import build_trend_figure


class TrendWindow(tk.Toplevel):
    """Pop-up window showing one user's BMI trend."""

    def __init__(
        self,
        parent: tk.Misc,
        user_name: str,
        dates: Sequence[datetime],
        values: Sequence[float],
    ) -> None:
        super().__init__(parent)
        self.title(f"BMI Trend - {user_name}")
        self.geometry("780x520")
        self.minsize(520, 380)

        if not values:
            ttk.Label(
                self,
                text=f"No records yet for {user_name}.\nCalculate a BMI first, then open the graph.",
                justify="center",
                padding=40,
            ).pack(expand=True)
            return

        figure = build_trend_figure(dates, values, user_name)
        canvas = FigureCanvasTkAgg(figure, master=self)
        canvas.draw()
        toolbar = NavigationToolbar2Tk(canvas, self, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

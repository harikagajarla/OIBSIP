"""Builds the matplotlib trend figure.

Kept separate from tkinter so the chart can be created (and tested) without
opening any window.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

import matplotlib.dates as mdates
from matplotlib.figure import Figure

from bmi_tracker import config


def build_trend_figure(dates: Sequence[datetime], values: Sequence[float], user_name: str) -> Figure:
    """Return a Figure showing BMI over time with coloured category bands."""
    if not values:
        raise ValueError("Cannot draw a trend graph without records.")
    if len(dates) != len(values):
        raise ValueError("dates and values must have the same length.")

    figure = Figure(figsize=(7.5, 4.5), dpi=100)
    axes = figure.add_subplot(111)

    low = min(15.0, min(values) - 1.0)
    high = max(35.0, max(values) + 1.0)
    bands = (
        ("Underweight", low, 18.5),
        ("Normal", 18.5, 25.0),
        ("Overweight", 25.0, 30.0),
        ("Obese", 30.0, high),
    )
    for name, start, end in bands:
        axes.axhspan(start, end, color=config.CATEGORY_COLOURS[name], alpha=0.12, label=name)

    axes.plot(list(dates), list(values), marker="o", linewidth=2, color="#37474F", label="Your BMI")
    axes.set_ylim(low, high)
    axes.set_title(f"BMI trend for {user_name}")
    axes.set_xlabel("Date")
    axes.set_ylabel("BMI")
    axes.grid(True, alpha=0.3)
    axes.legend(loc="upper left", fontsize=8)

    locator = mdates.AutoDateLocator()
    axes.xaxis.set_major_locator(locator)
    axes.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    figure.tight_layout()
    return figure

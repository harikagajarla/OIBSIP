"""Tests for the matplotlib trend graph (no window is opened)."""

from datetime import datetime
from io import BytesIO

import pytest

from bmi_tracker.ui.trend_chart import build_trend_figure

DATES = [datetime(2026, 1, 1), datetime(2026, 2, 1), datetime(2026, 3, 1)]
VALUES = [26.1, 25.4, 24.8]


def test_figure_contains_the_bmi_line_with_correct_data():
    figure = build_trend_figure(DATES, VALUES, "Alice")
    axes = figure.axes[0]
    assert len(axes.lines) == 1
    assert list(axes.lines[0].get_ydata()) == VALUES
    assert len(axes.lines[0].get_xdata()) == len(DATES)


def test_figure_title_mentions_the_user():
    assert "Alice" in build_trend_figure(DATES, VALUES, "Alice").axes[0].get_title()


def test_figure_axes_are_labelled():
    axes = build_trend_figure(DATES, VALUES, "Alice").axes[0]
    assert axes.get_xlabel() == "Date"
    assert axes.get_ylabel() == "BMI"


def test_y_axis_includes_extreme_values():
    axes = build_trend_figure(DATES, [8.0, 40.0, 55.0], "Alice").axes[0]
    low, high = axes.get_ylim()
    assert low <= 8.0 and high >= 55.0


def test_single_record_can_be_rendered_to_png():
    figure = build_trend_figure([datetime(2026, 1, 1)], [22.9], "Alice")
    buffer = BytesIO()
    figure.savefig(buffer, format="png")
    assert buffer.getbuffer().nbytes > 1000


def test_empty_data_is_rejected():
    with pytest.raises(ValueError):
        build_trend_figure([], [], "Alice")


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError):
        build_trend_figure(DATES, [22.0], "Alice")

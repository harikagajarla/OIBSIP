"""Core BMI logic: input validation, calculation and classification.

This module knows nothing about the GUI or the database, so it can be tested
on its own and reused (for example by a command-line tool).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from bmi_tracker import config
from bmi_tracker.exceptions import ValidationError

UNDERWEIGHT = "Underweight"
NORMAL = "Normal"
OVERWEIGHT = "Overweight"
OBESE = "Obese"

_USERNAME_PATTERN = re.compile(r"^[\w .'\-]+$")


@dataclass(frozen=True)
class BMIResult:
    """The outcome of one BMI calculation."""

    weight_kg: float
    height_m: float
    bmi: float  # already rounded to 2 decimal places
    category: str


def parse_positive_number(text: str | None, field_name: str, unit: str) -> float:
    """Convert text typed by the user into a positive, finite number.

    Raises ValidationError with a helpful message for empty, non-numeric,
    negative, zero, NaN and infinite input.
    """
    cleaned = "" if text is None else str(text).strip()
    if not cleaned:
        raise ValidationError(f"{field_name} is empty. Please enter a number in {unit}.")

    try:
        value = float(cleaned)
    except ValueError:
        hint = " Use a dot for decimals (for example 1.75)." if "," in cleaned else ""
        raise ValidationError(
            f"{field_name} must be a number such as 70 or 1.75, but you entered '{cleaned}'.{hint}"
        ) from None

    if math.isnan(value) or math.isinf(value):
        raise ValidationError(f"{field_name} must be a real number, but you entered '{cleaned}'.")
    if value < 0:
        raise ValidationError(f"{field_name} cannot be negative. Please enter a positive number in {unit}.")
    if value == 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def validate_weight(text: str | None) -> float:
    """Parse and range-check a weight in kilograms."""
    value = parse_positive_number(text, "Weight", "kg")
    if not config.MIN_WEIGHT_KG <= value <= config.MAX_WEIGHT_KG:
        raise ValidationError(
            f"Weight must be between {config.MIN_WEIGHT_KG:g} and {config.MAX_WEIGHT_KG:g} kg."
        )
    return value


def validate_height(text: str | None) -> float:
    """Parse and range-check a height in metres."""
    value = parse_positive_number(text, "Height", "metres")
    if not config.MIN_HEIGHT_M <= value <= config.MAX_HEIGHT_M:
        raise ValidationError(
            f"Height must be between {config.MIN_HEIGHT_M:g} and {config.MAX_HEIGHT_M:g} metres. "
            "If you used centimetres, convert to metres (175 cm = 1.75 m)."
        )
    return value


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Return BMI = weight / height^2, rounded to 2 decimal places."""
    if weight_kg <= 0 or height_m <= 0:
        raise ValidationError("Weight and height must be greater than zero.")
    return round(weight_kg / (height_m**2), 2)


def classify_bmi(bmi: float) -> str:
    """Return the health category for a BMI value.

    The rounded (2 decimal) BMI is classified, so the number the user sees
    always matches the category shown next to it.
    """
    if math.isnan(bmi) or math.isinf(bmi) or bmi <= 0:
        raise ValidationError("BMI must be a positive number.")
    if bmi < 18.5:
        return UNDERWEIGHT
    if bmi < 25:
        return NORMAL
    if bmi < 30:
        return OVERWEIGHT
    return OBESE


def compute_bmi_result(weight_text: str | None, height_text: str | None) -> BMIResult:
    """Validate raw text input, then calculate and classify the BMI."""
    weight = validate_weight(weight_text)
    height = validate_height(height_text)
    bmi = calculate_bmi(weight, height)
    return BMIResult(weight_kg=weight, height_m=height, bmi=bmi, category=classify_bmi(bmi))


def validate_username(name: str | None) -> str:
    """Return a cleaned user name or raise ValidationError."""
    cleaned = "" if name is None else str(name).strip()
    if not cleaned:
        raise ValidationError("User name is empty. Please type a name.")
    if len(cleaned) > config.MAX_USERNAME_LENGTH:
        raise ValidationError(f"User name is too long (maximum {config.MAX_USERNAME_LENGTH} characters).")
    if not _USERNAME_PATTERN.match(cleaned):
        raise ValidationError("User name may contain only letters, numbers, spaces and . ' - _")
    return cleaned

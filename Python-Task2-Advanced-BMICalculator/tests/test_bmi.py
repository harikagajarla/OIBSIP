"""Tests for the core BMI logic: calculation, classification and validation."""

import pytest

from bmi_tracker.core.bmi import (
    calculate_bmi,
    classify_bmi,
    compute_bmi_result,
    parse_positive_number,
    validate_height,
    validate_username,
    validate_weight,
)
from bmi_tracker.exceptions import ValidationError


# ----------------------------------------------------------- calculation
@pytest.mark.parametrize(
    "weight, height, expected",
    [
        (70, 1.75, 22.86),
        (50, 1.80, 15.43),
        (80, 1.75, 26.12),
        (100, 1.70, 34.60),
        (60, 1.60, 23.44),
    ],
)
def test_calculate_bmi_normal_cases(weight, height, expected):
    assert calculate_bmi(weight, height) == pytest.approx(expected, abs=0.001)


def test_calculate_bmi_rounds_to_two_decimals():
    result = calculate_bmi(70, 1.75)
    assert result == round(result, 2)


@pytest.mark.parametrize("weight, height", [(0, 1.7), (70, 0), (-1, 1.7), (70, -1.7)])
def test_calculate_bmi_rejects_non_positive_values(weight, height):
    with pytest.raises(ValidationError):
        calculate_bmi(weight, height)


# -------------------------------------------------------- classification
@pytest.mark.parametrize(
    "bmi, expected",
    [
        (10.0, "Underweight"),
        (18.49, "Underweight"),
        (18.5, "Normal"),
        (22.0, "Normal"),
        (24.9, "Normal"),
        (24.99, "Normal"),
        (25.0, "Overweight"),
        (27.5, "Overweight"),
        (29.9, "Overweight"),
        (29.99, "Overweight"),
        (30.0, "Obese"),
        (45.0, "Obese"),
    ],
)
def test_classify_bmi_boundaries(bmi, expected):
    assert classify_bmi(bmi) == expected


@pytest.mark.parametrize("bmi", [0, -3, float("nan"), float("inf")])
def test_classify_bmi_rejects_impossible_values(bmi):
    with pytest.raises(ValidationError):
        classify_bmi(bmi)


def test_category_matches_the_rounded_bmi_the_user_sees():
    # 24.996 is displayed as 25.0, so it must be classified Overweight.
    assert compute_bmi_result("24.996", "1.0").category == "Overweight"
    # 24.994 is displayed as 24.99, so it stays Normal.
    assert compute_bmi_result("24.994", "1.0").category == "Normal"


# ------------------------------------------------------------ validation
def test_compute_bmi_result_valid_input():
    result = compute_bmi_result("70", "1.75")
    assert result.weight_kg == 70.0
    assert result.height_m == 1.75
    assert result.bmi == pytest.approx(22.86)
    assert result.category == "Normal"


def test_compute_bmi_result_trims_whitespace():
    assert compute_bmi_result("  70 ", " 1.75  ").bmi == pytest.approx(22.86)


@pytest.mark.parametrize("text", ["abc", "5kg", "7,5", "1.2.3", "--5", "NaN", "inf", "-inf", "1e999"])
def test_non_numeric_input_is_rejected(text):
    with pytest.raises(ValidationError):
        parse_positive_number(text, "Weight", "kg")


@pytest.mark.parametrize("text", ["", "   ", None])
def test_empty_input_is_rejected(text):
    with pytest.raises(ValidationError, match="empty"):
        parse_positive_number(text, "Weight", "kg")


def test_negative_input_is_rejected_with_helpful_message():
    with pytest.raises(ValidationError, match="negative"):
        parse_positive_number("-70", "Weight", "kg")


def test_zero_is_rejected():
    with pytest.raises(ValidationError, match="greater than zero"):
        parse_positive_number("0", "Height", "metres")


def test_comma_decimal_gets_a_hint():
    with pytest.raises(ValidationError, match="dot"):
        parse_positive_number("1,75", "Height", "metres")


@pytest.mark.parametrize("text", ["1", "1.9", "501", "1000"])
def test_weight_outside_plausible_range_is_rejected(text):
    with pytest.raises(ValidationError, match="between"):
        validate_weight(text)


@pytest.mark.parametrize("text", ["0.3", "2.9", "175"])
def test_height_outside_plausible_range_is_rejected(text):
    with pytest.raises(ValidationError, match="metres"):
        validate_height(text)


@pytest.mark.parametrize("text", ["2", "70", "500"])
def test_weight_range_limits_are_inclusive(text):
    assert validate_weight(text) == float(text)


@pytest.mark.parametrize("text", ["0.5", "1.75", "2.8"])
def test_height_range_limits_are_inclusive(text):
    assert validate_height(text) == float(text)


def test_invalid_weight_reported_before_height():
    with pytest.raises(ValidationError, match="Weight"):
        compute_bmi_result("abc", "xyz")


# ------------------------------------------------------------- usernames
@pytest.mark.parametrize(
    "name, cleaned",
    [("Harika", "Harika"), ("  Ravi Kumar ", "Ravi Kumar"), ("O'Neil", "O'Neil"), ("user_1", "user_1"), ("A-B", "A-B")],
)
def test_valid_usernames(name, cleaned):
    assert validate_username(name) == cleaned


@pytest.mark.parametrize("name", ["", "   ", None, "x" * 41, "bad;name", "<script>", "a/b", "drop--table;"])
def test_invalid_usernames(name):
    with pytest.raises(ValidationError):
        validate_username(name)

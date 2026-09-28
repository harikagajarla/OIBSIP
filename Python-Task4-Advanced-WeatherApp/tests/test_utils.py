"""
Tests for app/utils.py - pure functions, no network or DB needed.

Run with:
    python -m unittest discover tests
"""

import unittest

from app import utils


class TestTemperatureConversion(unittest.TestCase):
    def test_celsius_to_fahrenheit_freezing(self):
        self.assertEqual(utils.celsius_to_fahrenheit(0), 32.0)

    def test_celsius_to_fahrenheit_boiling(self):
        self.assertEqual(utils.celsius_to_fahrenheit(100), 212.0)

    def test_celsius_to_fahrenheit_negative(self):
        self.assertEqual(utils.celsius_to_fahrenheit(-40), -40.0)

    def test_format_temperature_celsius(self):
        self.assertEqual(utils.format_temperature(25.4, "C"), "25.4°C")

    def test_format_temperature_fahrenheit(self):
        result = utils.format_temperature(0, "F")
        self.assertEqual(result, "32.0°F")


class TestIconMapping(unittest.TestCase):
    def test_known_condition(self):
        self.assertEqual(utils.icon_file_for_condition("Rain"), "rain.png")

    def test_unknown_condition_falls_back_to_default(self):
        self.assertEqual(utils.icon_file_for_condition("Tornado"), utils.DEFAULT_ICON)


class TestCityValidation(unittest.TestCase):
    def test_empty_string_invalid(self):
        self.assertFalse(utils.is_valid_city_name(""))

    def test_whitespace_only_invalid(self):
        self.assertFalse(utils.is_valid_city_name("   "))

    def test_normal_city_valid(self):
        self.assertTrue(utils.is_valid_city_name("Hyderabad"))

    def test_too_long_invalid(self):
        self.assertFalse(utils.is_valid_city_name("a" * 101))


class TestVisibilityConversion(unittest.TestCase):
    def test_meters_to_km(self):
        self.assertEqual(utils.meters_to_km(10000), 10.0)

    def test_meters_to_km_rounding(self):
        self.assertEqual(utils.meters_to_km(4500), 4.5)


if __name__ == "__main__":
    unittest.main()

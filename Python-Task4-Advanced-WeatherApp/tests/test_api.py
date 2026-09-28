"""
Tests for response parsing in weather_service.py (renamed conceptually
from "test_api" per the requested checklist - these cover "API response
parsing" and "invalid API response handling", using fixture JSON rather
than real network calls, so tests run offline and deterministically).
"""

import unittest

from app import weather_service


SAMPLE_CURRENT_WEATHER = {
    "name": "Hyderabad",
    "sys": {"country": "IN", "sunrise": 1695000000, "sunset": 1695040000},
    "main": {"temp": 29.5, "feels_like": 32.1, "humidity": 60, "pressure": 1008},
    "weather": [{"main": "Clouds", "description": "scattered clouds"}],
    "wind": {"speed": 3.6},
    "visibility": 8000,
    "timezone": 19800,
}

SAMPLE_FORECAST = {
    "list": [
        {
            "dt": 1695006000,
            "dt_txt": "2023-09-18 12:00:00",
            "main": {"temp": 28.0, "humidity": 55},
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "wind": {"speed": 2.1},
        },
        {
            "dt": 1695016800,
            "dt_txt": "2023-09-18 15:00:00",
            "main": {"temp": 31.0, "humidity": 50},
            "weather": [{"main": "Clouds", "description": "few clouds"}],
            "wind": {"speed": 3.0},
        },
        {
            "dt": 1695092400,
            "dt_txt": "2023-09-19 12:00:00",
            "main": {"temp": 27.0, "humidity": 65},
            "weather": [{"main": "Rain", "description": "light rain"}],
            "wind": {"speed": 4.2},
        },
    ]
}


class TestParseCurrentWeather(unittest.TestCase):
    def test_parses_valid_response(self):
        result = weather_service.parse_current_weather(SAMPLE_CURRENT_WEATHER)
        self.assertEqual(result.city, "Hyderabad")
        self.assertEqual(result.country, "IN")
        self.assertEqual(result.temperature_c, 29.5)
        self.assertEqual(result.condition_main, "Clouds")
        self.assertEqual(result.visibility_km, 8.0)

    def test_missing_required_field_raises(self):
        broken = {"name": "Hyderabad"}  # missing sys, main, weather
        with self.assertRaises(weather_service.MalformedResponseError):
            weather_service.parse_current_weather(broken)

    def test_empty_weather_list_raises(self):
        broken = dict(SAMPLE_CURRENT_WEATHER)
        broken["weather"] = []
        with self.assertRaises(weather_service.MalformedResponseError):
            weather_service.parse_current_weather(broken)


class TestParseForecast(unittest.TestCase):
    def test_groups_entries_by_day(self):
        result = weather_service.parse_forecast(SAMPLE_FORECAST)
        self.assertEqual(len(result), 2)  # two distinct dates in the sample

    def test_aggregates_min_max_correctly(self):
        result = weather_service.parse_forecast(SAMPLE_FORECAST)
        day_one = result[0]
        self.assertEqual(day_one.temp_min_c, 28.0)
        self.assertEqual(day_one.temp_max_c, 31.0)

    def test_empty_list_raises(self):
        with self.assertRaises(weather_service.MalformedResponseError):
            weather_service.parse_forecast({"list": []})


if __name__ == "__main__":
    unittest.main()

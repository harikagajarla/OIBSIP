"""
Small, pure helper functions with no side effects.

Kept separate so they're trivial to unit test without touching the
network, the database, or the GUI.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Maps OpenWeatherMap's "main" condition field to our local icon files.
# See: https://openweathermap.org/weather-conditions
CONDITION_TO_ICON = {
    "Clear": "clear.png",
    "Clouds": "clouds.png",
    "Rain": "rain.png",
    "Drizzle": "drizzle.png",
    "Thunderstorm": "thunderstorm.png",
    "Snow": "snow.png",
    "Mist": "mist.png",
    "Fog": "mist.png",
    "Haze": "mist.png",
    "Smoke": "mist.png",
}

DEFAULT_ICON = "clear.png"


def icon_file_for_condition(condition: str) -> str:
    """Return the local icon filename for a given weather 'main' condition."""
    return CONDITION_TO_ICON.get(condition, DEFAULT_ICON)


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert a Celsius temperature to Fahrenheit, rounded to 1 decimal."""
    return round((celsius * 9 / 5) + 32, 1)


def format_temperature(celsius: float, unit: str) -> str:
    """Format a Celsius value for display in the requested unit ('C' or 'F')."""
    if unit.upper() == "F":
        return f"{celsius_to_fahrenheit(celsius):.1f}°F"
    return f"{celsius:.1f}°C"


def unix_to_local_time(unix_timestamp: int, tz_offset_seconds: int = 0) -> str:
    """Convert a UTC unix timestamp + city's UTC offset into 'HH:MM' local time."""
    dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    local_dt = dt.astimezone(timezone.utc)
    local_dt = local_dt.replace(tzinfo=None)
    from datetime import timedelta

    local_dt = local_dt + timedelta(seconds=tz_offset_seconds)
    return local_dt.strftime("%H:%M")


def unix_to_date_label(unix_timestamp: int) -> str:
    """Convert a unix timestamp into a short date label, e.g. 'Mon, 23 Sep'."""
    dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    return dt.strftime("%a, %d %b")


def is_valid_city_name(city: str) -> bool:
    """Basic sanity check before making an API call - not exhaustive,
    the API itself is the source of truth for whether a city exists."""
    if not city or not city.strip():
        return False
    if len(city.strip()) > 100:
        return False
    return True


def meters_to_km(meters: int) -> float:
    """Convert visibility from meters (API default) to kilometers."""
    return round(meters / 1000, 1)

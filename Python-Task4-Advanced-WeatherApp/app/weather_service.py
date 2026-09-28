"""
Business logic layer.

Takes the raw JSON dicts from api.py and turns them into clean,
typed Python objects the UI can use directly. Also does the
3-hour -> daily forecast aggregation, since OpenWeatherMap's free
tier only offers 3-hour step data, not a native daily endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app import utils


class MalformedResponseError(Exception):
    """Raised when the API response is missing fields we depend on."""


@dataclass
class CurrentWeather:
    city: str
    country: str
    temperature_c: float
    feels_like_c: float
    condition_main: str
    condition_description: str
    humidity_percent: int
    wind_speed_ms: float
    pressure_hpa: int
    visibility_km: float
    sunrise_unix: int
    sunset_unix: int
    timezone_offset_seconds: int
    last_updated: str  # formatted at fetch time


@dataclass
class ForecastDay:
    date_label: str
    condition_main: str
    condition_description: str
    temp_min_c: float
    temp_max_c: float
    humidity_percent: int
    wind_speed_ms: float


def _require(d: dict, *keys):
    """Walk nested dict keys, raising MalformedResponseError if any is missing."""
    current = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise MalformedResponseError(f"Missing expected field: {' -> '.join(map(str, keys))}")
        current = current[key]
    return current


def parse_current_weather(raw: dict) -> CurrentWeather:
    """Convert raw OpenWeatherMap 'current weather' JSON into a CurrentWeather object."""
    try:
        weather_list = _require(raw, "weather")
        if not weather_list:
            raise MalformedResponseError("Weather condition list is empty.")

        return CurrentWeather(
            city=_require(raw, "name"),
            country=_require(raw, "sys", "country"),
            temperature_c=float(_require(raw, "main", "temp")),
            feels_like_c=float(_require(raw, "main", "feels_like")),
            condition_main=weather_list[0].get("main", "Clear"),
            condition_description=weather_list[0].get("description", "").title(),
            humidity_percent=int(_require(raw, "main", "humidity")),
            wind_speed_ms=float(_require(raw, "wind", "speed")),
            pressure_hpa=int(_require(raw, "main", "pressure")),
            visibility_km=utils.meters_to_km(raw.get("visibility", 10000)),
            sunrise_unix=int(_require(raw, "sys", "sunrise")),
            sunset_unix=int(_require(raw, "sys", "sunset")),
            timezone_offset_seconds=int(raw.get("timezone", 0)),
            last_updated=datetime.now().strftime("%d %b %Y, %H:%M"),
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise MalformedResponseError(f"Could not parse current weather data: {exc}") from exc


def parse_forecast(raw: dict) -> list[ForecastDay]:
    """Aggregate OpenWeatherMap's 3-hour-step forecast into one entry per day.

    Strategy: group the 3-hour entries by calendar date, then take the
    min/max temperature across that day and use the entry closest to
    midday as the "representative" condition (more meaningful than the
    first entry, which might be overnight).
    """
    try:
        entries = _require(raw, "list")
        if not entries:
            raise MalformedResponseError("Forecast list is empty.")

        days: dict[str, list[dict]] = {}
        for entry in entries:
            dt_txt = entry.get("dt_txt", "")
            date_part = dt_txt.split(" ")[0] if dt_txt else None
            if not date_part:
                continue
            days.setdefault(date_part, []).append(entry)

        forecast_days: list[ForecastDay] = []
        for date_part, day_entries in list(days.items())[:5]:
            temps = [e["main"]["temp"] for e in day_entries if "main" in e]
            humidities = [e["main"]["humidity"] for e in day_entries if "main" in e]
            winds = [e["wind"]["speed"] for e in day_entries if "wind" in e]

            # Pick the entry closest to 12:00 as representative for the icon/description
            def hour_of(entry):
                try:
                    return int(entry["dt_txt"].split(" ")[1].split(":")[0])
                except (KeyError, IndexError, ValueError):
                    return 0

            representative = min(day_entries, key=lambda e: abs(hour_of(e) - 12))
            weather_list = representative.get("weather", [{}])
            condition_main = weather_list[0].get("main", "Clear") if weather_list else "Clear"
            condition_description = weather_list[0].get("description", "").title() if weather_list else ""

            forecast_days.append(
                ForecastDay(
                    date_label=utils.unix_to_date_label(representative.get("dt", 0)),
                    condition_main=condition_main,
                    condition_description=condition_description,
                    temp_min_c=round(min(temps), 1) if temps else 0.0,
                    temp_max_c=round(max(temps), 1) if temps else 0.0,
                    humidity_percent=round(sum(humidities) / len(humidities)) if humidities else 0,
                    wind_speed_ms=round(sum(winds) / len(winds), 1) if winds else 0.0,
                )
            )

        return forecast_days
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise MalformedResponseError(f"Could not parse forecast data: {exc}") from exc

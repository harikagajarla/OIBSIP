"""
Raw network layer.

Every function here does ONE thing: call an HTTP endpoint and return
parsed JSON, or raise a typed exception. No business logic (unit
conversion, aggregation, formatting) belongs in this file - that
lives in weather_service.py.
"""

from __future__ import annotations

import requests

from app import config


class WeatherAPIError(Exception):
    """Base class for all weather-API related errors."""


class CityNotFoundError(WeatherAPIError):
    """Raised when the API can't find the requested city."""


class InvalidAPIKeyError(WeatherAPIError):
    """Raised on HTTP 401 - key missing, wrong, or not yet activated."""


class RateLimitError(WeatherAPIError):
    """Raised on HTTP 429 - too many requests."""


class NetworkError(WeatherAPIError):
    """Raised when the request fails before we even get a response
    (no internet, DNS failure, timeout)."""


def _get(url: str, params: dict) -> dict:
    """Shared GET helper with consistent error handling."""
    try:
        response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.Timeout as exc:
        raise NetworkError("The request timed out. Check your internet connection.") from exc
    except requests.exceptions.ConnectionError as exc:
        raise NetworkError("Could not connect. Check your internet connection.") from exc
    except requests.exceptions.RequestException as exc:
        raise NetworkError(f"Network error: {exc}") from exc

    if response.status_code == 401:
        raise InvalidAPIKeyError(
            "Invalid or inactive API key. New keys can take up to 2 hours "
            "to activate after creation on OpenWeatherMap."
        )
    if response.status_code == 404:
        raise CityNotFoundError("City not found. Check the spelling and try again.")
    if response.status_code == 429:
        raise RateLimitError("Too many requests. Please wait a moment and try again.")
    if response.status_code != 200:
        raise WeatherAPIError(f"Unexpected API error (status {response.status_code}).")

    try:
        return response.json()
    except ValueError as exc:
        raise WeatherAPIError("Received a malformed response from the weather API.") from exc


def fetch_current_weather(city: str) -> dict:
    """Fetch current weather for a city name. Returns raw JSON dict."""
    if not city or not city.strip():
        raise CityNotFoundError("Please enter a city name.")

    params = {
        "q": city.strip(),
        "appid": config.WEATHER_API_KEY,
        "units": "metric",  # always fetch in Celsius; convert in weather_service.py
    }
    return _get(config.CURRENT_WEATHER_URL, params)


def fetch_forecast(city: str) -> dict:
    """Fetch the 5-day / 3-hour forecast for a city name. Returns raw JSON dict."""
    if not city or not city.strip():
        raise CityNotFoundError("Please enter a city name.")

    params = {
        "q": city.strip(),
        "appid": config.WEATHER_API_KEY,
        "units": "metric",
    }
    return _get(config.FORECAST_URL, params)


def fetch_ip_location() -> dict | None:
    """Best-effort, free, no-key IP-based geolocation.

    Returns a dict like {"city": "...", "country": "..."} or None if
    the lookup fails. This is approximate (city-level), not GPS - it
    is not a substitute for a real location permission API, which
    would require a paid/complex setup we're deliberately avoiding.
    """
    try:
        response = requests.get(config.IP_GEOLOCATION_URL, timeout=config.REQUEST_TIMEOUT_SECONDS)
        data = response.json()
        if data.get("status") == "success" and data.get("city"):
            return {"city": data["city"], "country": data.get("countryCode", "")}
    except requests.exceptions.RequestException:
        pass
    return None

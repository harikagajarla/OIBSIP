"""
Standalone API key verification script.

Run this BEFORE launching the GUI to confirm your OpenWeatherMap key
is active and working:

    python verify_api_key.py

It does not depend on any other app module beyond config/api, so it
also doubles as a quick way to isolate "is this an API problem?" from
"is this a GUI problem?" while troubleshooting.
"""

from app import api, config


def main() -> None:
    print("Checking .env configuration...")
    if not config.WEATHER_API_KEY:
        print("FAILED: No WEATHER_API_KEY found in .env.")
        print("  1. Copy .env.example to .env")
        print("  2. Paste your OpenWeatherMap key into .env")
        return

    print(f"Found a key ending in ...{config.WEATHER_API_KEY[-4:]}")
    print("Calling OpenWeatherMap for a test city (London)...")

    try:
        data = api.fetch_current_weather("London")
    except api.InvalidAPIKeyError:
        print("FAILED: Key was rejected (401).")
        print("  New keys can take up to ~1 hour to activate. Wait and retry.")
        return
    except api.NetworkError as exc:
        print(f"FAILED: Network problem - {exc}")
        return
    except api.WeatherAPIError as exc:
        print(f"FAILED: {exc}")
        return

    city = data.get("name", "?")
    temp = data.get("main", {}).get("temp", "?")
    print(f"SUCCESS: Received live data for {city} ({temp}°C).")
    print("Your API key is working. You can now run: python run.py")


if __name__ == "__main__":
    main()

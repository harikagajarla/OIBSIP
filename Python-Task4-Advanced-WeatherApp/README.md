# Advanced Weather App

A desktop weather application built with Python and CustomTkinter, developed as
**Task 4** of the Oasis Infobyte Python Programming Internship.

## Overview

Search any city to view live current weather and a 5-day forecast, switch
between Celsius and Fahrenheit, save favorite cities, and browse your recent
search history — all backed by a local SQLite database and the OpenWeatherMap
API, with the GUI kept responsive via background threading.

## Features

- 🔍 Search weather by city name, with graceful handling of invalid cities
- 🌡️ Current conditions: temperature, feels-like, humidity, wind, pressure,
  visibility, sunrise/sunset, last-updated time
- 📅 5-day forecast (aggregated from OpenWeatherMap's 3-hour-step data)
- 🌡️ Celsius / Fahrenheit toggle, applied live across all displayed values
- ⭐ Favorite cities — add, remove, and jump back to them with one click
- 🕘 Search history stored in SQLite, with click-to-search-again and Clear
- 🔄 Manual refresh + automatic background refresh (throttled to limit API calls)
- 📍 Optional "Use My Location" via free IP-based geolocation (see Limitations)
- 🎨 Condition icons (clear, clouds, rain, drizzle, thunderstorm, snow, mist/fog)
- ⏳ Non-blocking loading states — the UI never freezes during a request
- 🛡️ Handles invalid API keys, invalid cities, no internet, timeouts, rate
  limits, and malformed responses without crashing

## Technologies Used

- Python 3.12
- CustomTkinter (GUI)
- `requests` (HTTP)
- OpenWeatherMap API (current weather + forecast)
- SQLite (search history, favorites)
- `python-dotenv` (secret management)
- Pillow (icon rendering)
- `pytest` (automated tests)

## Project Structure

```
Python-Task4-Advanced-WeatherApp/
├── app/
│   ├── main.py            # Entry point orchestration
│   ├── api.py              # Raw HTTP calls + typed errors
│   ├── weather_service.py  # Parsing, forecast aggregation, unit conversion
│   ├── database.py         # SQLite repos: search_history, favorite_cities
│   ├── config.py           # .env loading, constants
│   ├── ui.py                # CustomTkinter GUI
│   └── utils.py             # Pure helper functions
├── assets/weather_icons/    # Local condition icons
├── screenshots/             # Add demo screenshots here
├── tests/                   # pytest suite (27 tests)
├── verify_api_key.py        # Standalone script to test your API key
├── .env.example
├── .gitignore
├── requirements.txt
└── run.py                   # python run.py
```

## How It Works

`api.py` makes raw HTTP calls and raises typed exceptions (`CityNotFoundError`,
`InvalidAPIKeyError`, `RateLimitError`, `NetworkError`). `weather_service.py`
turns the raw JSON into clean `CurrentWeather` / `ForecastDay` objects — this is
also where OpenWeatherMap's 3-hour forecast steps get grouped into one entry
per day. `ui.py` runs every network call on a background thread and posts
results back to the main thread, so the window never freezes. `database.py`
persists history and favorites with parameterized SQLite queries.

## API Setup

1. Create a free account at [openweathermap.org](https://home.openweathermap.org/users/sign_up).
2. Get your key from the [API keys page](https://home.openweathermap.org/api_keys).
3. New keys can take up to ~1 hour to activate — a 401 error right after
   creating one is expected; just wait and retry.

**Never commit a real key.** This project keeps secrets out of source control:

- `.env` — your real key, listed in `.gitignore`, never pushed to GitHub
- `.env.example` — a template showing the expected variable name only

## Installation (Windows 10/11, PowerShell)

```powershell
cd Python-Task4-Advanced-WeatherApp
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env   # paste your real API key, save, close
python verify_api_key.py   # confirm the key works
python run.py
```

## Usage

Type a city and press **Search** or Enter. Use the **Celsius/Fahrenheit**
toggle to switch units, **Refresh** to re-fetch the current city, **☆ Add to
Favorites** to save it, and click any favorite or history entry to reload it
instantly. **Clear** wipes search history.

## Database

`weather_app.db` (SQLite, auto-created on first run, git-ignored) holds:

- `search_history` — city, country, timestamp, temperature, condition
- `favorite_cities` — city, country (unique pair)

## Error Handling

Invalid API key, city not found, no internet, request timeout, API rate
limiting, and malformed/missing response fields are all caught explicitly and
shown as a status message — the app never crashes on a normal user or API
error.

## Testing

27 automated tests cover temperature conversion, forecast parsing/aggregation,
malformed-response handling, and all database operations:

```powershell
pip install pytest
python -m pytest tests/ -v
```

Manual GUI testing checklist is in the project handoff notes (search, current
weather, forecast, unit toggle, favorites, history, refresh, invalid city, and
offline behavior were all verified before this project was marked complete).

## Security Considerations

The API key lives only in `.env`, which is excluded from version control via
`.gitignore`. `config.py` fails fast with a clear message if the key is
missing, instead of leaking a `None` value into a request. The SQLite database
is also git-ignored since it may contain your personal search history.

## Limitations

- OpenWeatherMap's free tier returns forecast data in 3-hour steps, not a
  native daily endpoint — this app aggregates that into daily min/max/condition
  itself, which is an approximation, not official daily data.
- "Use My Location" uses free IP-based geolocation (city-level accuracy), not
  true GPS — true device location would require a paid or OS-permission-based
  service, which this project intentionally avoids.
- Auto-refresh is throttled to a conservative interval to stay well within the
  free API tier's rate limits.

## Future Enhancements

- Interactive weather maps
- Hourly (not just daily) forecast view
- Air quality index
- Severe weather alerts
- True GPS-based location (would require a paid/native API)

---
Built for the **Oasis Infobyte Python Programming Internship — Task 4**.

"""
GUI layer, built with CustomTkinter.

Design rule followed throughout: every network call runs in a
background thread (threading.Thread) and posts its result back to
the main thread with `self.after(0, callback)`. Tkinter widgets must
only ever be touched from the main thread - this pattern keeps the
window responsive and avoids crashes from cross-thread widget access.
"""

from __future__ import annotations

import threading
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from app import api, config, database, utils, weather_service

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "weather_icons"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def load_icon(condition_main: str, size=(64, 64)) -> ctk.CTkImage:
    filename = utils.icon_file_for_condition(condition_main)
    path = ICONS_DIR / filename
    pil_image = Image.open(path)
    return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)


class WeatherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(config.APP_TITLE)
        self.geometry("980x680")
        self.minsize(860, 620)

        # State
        self.unit = "C"  # or "F"
        self.current_city = ""
        self.current_country = ""
        self._is_loading = False

        # DB
        self.db_conn = database.get_connection()
        self.history_repo = database.SearchHistoryRepo(self.db_conn)
        self.favorites_repo = database.FavoriteCitiesRepo(self.db_conn)

        self._build_layout()
        self._refresh_favorites_panel()
        self._refresh_history_panel()

        # Auto-refresh (safe: only re-fetches if a city is already loaded)
        self.after(config.AUTO_REFRESH_INTERVAL_MS, self._auto_refresh)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top search bar -------------------------------------------------
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))
        search_frame.grid_columnconfigure(0, weight=1)

        self.city_entry = ctk.CTkEntry(search_frame, placeholder_text="Search city, e.g. Hyderabad")
        self.city_entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=12)
        self.city_entry.bind("<Return>", lambda e: self._on_search())

        ctk.CTkButton(search_frame, text="Search", width=90, command=self._on_search).grid(
            row=0, column=1, padx=4, pady=12
        )
        ctk.CTkButton(
            search_frame, text="📍 Use My Location", width=150, command=self._on_use_location
        ).grid(row=0, column=2, padx=(4, 12), pady=12)

        # --- Left column: current weather + forecast ------------------------
        left_col = ctk.CTkFrame(self)
        left_col.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=8)
        left_col.grid_rowconfigure(1, weight=0)
        left_col.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(left_col, text="Search a city to get started.", text_color="gray")
        self.status_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        # Current weather card
        self.current_card = ctk.CTkFrame(left_col, corner_radius=12)
        self.current_card.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        self._build_current_card(self.current_card)

        # Unit toggle + refresh
        controls = ctk.CTkFrame(left_col, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=12, pady=4)
        self.unit_segment = ctk.CTkSegmentedButton(
            controls, values=["Celsius", "Fahrenheit"], command=self._on_unit_change
        )
        self.unit_segment.set("Celsius")
        self.unit_segment.pack(side="left", padx=(0, 12))
        ctk.CTkButton(controls, text="🔄 Refresh", width=100, command=self._on_refresh).pack(side="left")
        self.favorite_button = ctk.CTkButton(
            controls, text="☆ Add to Favorites", width=160, command=self._on_toggle_favorite
        )
        self.favorite_button.pack(side="left", padx=12)

        # Forecast row
        forecast_label = ctk.CTkLabel(left_col, text="5-Day Forecast", font=ctk.CTkFont(size=16, weight="bold"))
        forecast_label.grid(row=3, column=0, sticky="w", padx=16, pady=(16, 4))

        self.forecast_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        self.forecast_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
        for i in range(5):
            self.forecast_frame.grid_columnconfigure(i, weight=1)

        # --- Right column: favorites + history -------------------------------
        right_col = ctk.CTkFrame(self)
        right_col.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=8)
        right_col.grid_rowconfigure(1, weight=1)
        right_col.grid_rowconfigure(3, weight=1)
        right_col.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_col, text="⭐ Favorite Cities", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )
        self.favorites_list = ctk.CTkScrollableFrame(right_col, height=180)
        self.favorites_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        history_header = ctk.CTkFrame(right_col, fg_color="transparent")
        history_header.grid(row=2, column=0, sticky="ew", padx=12, pady=(8, 4))
        ctk.CTkLabel(history_header, text="🕘 Search History", font=ctk.CTkFont(size=15, weight="bold")).pack(
            side="left"
        )
        ctk.CTkButton(history_header, text="Clear", width=60, fg_color="gray30", command=self._on_clear_history).pack(
            side="right"
        )
        self.history_list = ctk.CTkScrollableFrame(right_col, height=180)
        self.history_list.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_current_card(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)

        self.city_title_label = ctk.CTkLabel(parent, text="—", font=ctk.CTkFont(size=22, weight="bold"))
        self.city_title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 0))

        self.icon_label = ctk.CTkLabel(parent, text="")
        self.icon_label.grid(row=1, column=0, rowspan=2, sticky="w", padx=16, pady=8)

        self.temp_label = ctk.CTkLabel(parent, text="—", font=ctk.CTkFont(size=42, weight="bold"))
        self.temp_label.grid(row=1, column=1, sticky="w", pady=(8, 0))

        self.condition_label = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(size=15))
        self.condition_label.grid(row=2, column=1, sticky="w")

        details_frame = ctk.CTkFrame(parent, fg_color="transparent")
        details_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 16))
        for i in range(4):
            details_frame.grid_columnconfigure(i, weight=1)

        self.detail_labels = {}
        detail_keys = [
            "Feels like", "Humidity", "Wind", "Pressure",
            "Visibility", "Sunrise", "Sunset", "Updated",
        ]
        for i, key in enumerate(detail_keys):
            row, col = divmod(i, 4)
            box = ctk.CTkFrame(details_frame, fg_color="gray20", corner_radius=8)
            box.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
            ctk.CTkLabel(box, text=key, font=ctk.CTkFont(size=11), text_color="gray70").pack(pady=(6, 0))
            value_label = ctk.CTkLabel(box, text="—", font=ctk.CTkFont(size=13, weight="bold"))
            value_label.pack(pady=(0, 6))
            self.detail_labels[key] = value_label

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_search(self):
        city = self.city_entry.get().strip()
        if not utils.is_valid_city_name(city):
            self._set_status("Please enter a valid city name.", error=True)
            return
        self._load_weather_for(city)

    def _on_use_location(self):
        self._set_status("Detecting approximate location…")

        def worker():
            location = api.fetch_ip_location()
            self.after(0, lambda: self._handle_location_result(location))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_location_result(self, location: dict | None):
        if location:
            self.city_entry.delete(0, "end")
            self.city_entry.insert(0, location["city"])
            self._load_weather_for(location["city"])
        else:
            self._set_status(
                "Couldn't detect location automatically (this uses free IP-based "
                "geolocation, not GPS). Please search by city name instead.",
                error=True,
            )

    def _on_unit_change(self, value: str):
        self.unit = "F" if value == "Fahrenheit" else "C"
        if self._last_current is not None:
            self._render_current(self._last_current)
        if self._last_forecast is not None:
            self._render_forecast(self._last_forecast)

    def _on_refresh(self):
        if self.current_city:
            self._load_weather_for(self.current_city, is_refresh=True)

    def _auto_refresh(self):
        if self.current_city and not self._is_loading:
            self._load_weather_for(self.current_city, is_refresh=True)
        self.after(config.AUTO_REFRESH_INTERVAL_MS, self._auto_refresh)

    def _on_toggle_favorite(self):
        if not self.current_city:
            return
        if self.favorites_repo.is_favorite(self.current_city, self.current_country):
            self.favorites_repo.remove(self.current_city, self.current_country)
        else:
            self.favorites_repo.add(self.current_city, self.current_country)
        self._refresh_favorites_panel()
        self._update_favorite_button()

    def _on_clear_history(self):
        self.history_repo.clear()
        self._refresh_history_panel()

    # ------------------------------------------------------------------
    # Core loading flow (threaded)
    # ------------------------------------------------------------------
    _last_current = None
    _last_forecast = None

    def _load_weather_for(self, city: str, is_refresh: bool = False):
        if self._is_loading:
            return  # prevent duplicate concurrent requests
        self._is_loading = True
        self._set_status(f"Loading weather for {city}…")

        def worker():
            try:
                current_raw = api.fetch_current_weather(city)
                current = weather_service.parse_current_weather(current_raw)

                forecast_raw = api.fetch_forecast(city)
                forecast = weather_service.parse_forecast(forecast_raw)

                self.after(0, lambda: self._handle_success(current, forecast, is_refresh))
            except (api.WeatherAPIError, weather_service.MalformedResponseError) as exc:
                # Capture the message now - Python clears the exception
                # variable once this except block exits, so the lambda
                # below can't safely reference `exc` directly.
                error_message = str(exc)
                self.after(0, lambda: self._handle_failure(error_message))
            finally:
                self.after(0, self._clear_loading_flag)

        threading.Thread(target=worker, daemon=True).start()

    def _clear_loading_flag(self):
        self._is_loading = False

    def _handle_success(self, current: weather_service.CurrentWeather, forecast, is_refresh: bool):
        self.current_city = current.city
        self.current_country = current.country
        self._last_current = current
        self._last_forecast = forecast

        self._render_current(current)
        self._render_forecast(forecast)
        self._update_favorite_button()
        self._set_status("")

        if not is_refresh:
            self.history_repo.add(current.city, current.country, current.temperature_c, current.condition_main)
            self._refresh_history_panel()

    def _handle_failure(self, message: str):
        self._set_status(message, error=True)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render_current(self, current: weather_service.CurrentWeather):
        self.city_title_label.configure(text=f"{current.city}, {current.country}")
        self.temp_label.configure(text=utils.format_temperature(current.temperature_c, self.unit))
        self.condition_label.configure(text=current.condition_description)
        self.icon_label.configure(image=load_icon(current.condition_main, size=(72, 72)))

        sunrise = utils.unix_to_local_time(current.sunrise_unix, current.timezone_offset_seconds)
        sunset = utils.unix_to_local_time(current.sunset_unix, current.timezone_offset_seconds)

        self.detail_labels["Feels like"].configure(text=utils.format_temperature(current.feels_like_c, self.unit))
        self.detail_labels["Humidity"].configure(text=f"{current.humidity_percent}%")
        self.detail_labels["Wind"].configure(text=f"{current.wind_speed_ms} m/s")
        self.detail_labels["Pressure"].configure(text=f"{current.pressure_hpa} hPa")
        self.detail_labels["Visibility"].configure(text=f"{current.visibility_km} km")
        self.detail_labels["Sunrise"].configure(text=sunrise)
        self.detail_labels["Sunset"].configure(text=sunset)
        self.detail_labels["Updated"].configure(text=current.last_updated)

    def _render_forecast(self, forecast):
        for widget in self.forecast_frame.winfo_children():
            widget.destroy()

        for i, day in enumerate(forecast):
            card = ctk.CTkFrame(self.forecast_frame, corner_radius=10)
            card.grid(row=0, column=i, sticky="ew", padx=4)

            ctk.CTkLabel(card, text=day.date_label, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 2))
            ctk.CTkLabel(card, image=load_icon(day.condition_main, size=(40, 40)), text="").pack(pady=2)
            ctk.CTkLabel(card, text=day.condition_description, font=ctk.CTkFont(size=10), wraplength=100).pack()
            temp_text = (
                f"{utils.format_temperature(day.temp_max_c, self.unit)} / "
                f"{utils.format_temperature(day.temp_min_c, self.unit)}"
            )
            ctk.CTkLabel(card, text=temp_text, font=ctk.CTkFont(size=12)).pack(pady=(4, 2))
            ctk.CTkLabel(card, text=f"💧 {day.humidity_percent}%  💨 {day.wind_speed_ms} m/s",
                         font=ctk.CTkFont(size=10), text_color="gray70").pack(pady=(0, 10))

    def _refresh_favorites_panel(self):
        for widget in self.favorites_list.winfo_children():
            widget.destroy()

        favorites = self.favorites_repo.get_all()
        if not favorites:
            ctk.CTkLabel(self.favorites_list, text="No favorites yet.", text_color="gray").pack(pady=8)
            return

        for fav in favorites:
            row = ctk.CTkFrame(self.favorites_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            label_text = f"{fav.city}, {fav.country}" if fav.country else fav.city
            ctk.CTkButton(
                row, text=label_text, anchor="w", fg_color="transparent", hover_color="gray25",
                command=lambda c=fav.city: self._load_weather_for(c),
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="✕", width=28, fg_color="gray30",
                command=lambda c=fav.city, co=fav.country: self._remove_favorite(c, co),
            ).pack(side="right")

    def _remove_favorite(self, city: str, country: str):
        self.favorites_repo.remove(city, country)
        self._refresh_favorites_panel()
        self._update_favorite_button()

    def _refresh_history_panel(self):
        for widget in self.history_list.winfo_children():
            widget.destroy()

        history = self.history_repo.get_recent(limit=15)
        if not history:
            ctk.CTkLabel(self.history_list, text="No searches yet.", text_color="gray").pack(pady=8)
            return

        for entry in history:
            label_text = f"{entry.city} · {entry.temperature_c:.0f}°C · {entry.searched_at[5:16]}"
            ctk.CTkButton(
                self.history_list, text=label_text, anchor="w", fg_color="transparent", hover_color="gray25",
                command=lambda c=entry.city: self._load_weather_for(c),
            ).pack(fill="x", pady=2)

    def _update_favorite_button(self):
        if not self.current_city:
            return
        is_fav = self.favorites_repo.is_favorite(self.current_city, self.current_country)
        self.favorite_button.configure(text="★ In Favorites" if is_fav else "☆ Add to Favorites")

    def _set_status(self, message: str, error: bool = False):
        self.status_label.configure(text=message, text_color=("red" if error else "gray"))

    def on_close(self):
        self.db_conn.close()
        self.destroy()

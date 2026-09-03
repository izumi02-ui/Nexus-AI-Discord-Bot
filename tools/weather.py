"""
Project Nexus

Weather Tool

Live weather from Open-Meteo (free, no API key, no signup). Replaces the old
placeholder that returned "Weather integration is under development." with a
confidence of 1.0 - which the model then repeated as if it were a forecast.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._geo import geocode
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger
from utils.time_utils import now_utc

WMO = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "rain showers",
    82: "violent rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}

_PLACE_RE = re.compile(
    r"(?:weather|forecast|temperature|rain|snow|humidity|wind|storm)"
    r"[^?!.]*?\b(?:in|at|for|near)\s+(?P<place>[A-Za-z .,'-]{2,60}?)"
    r"(?:\s+(?:today|tomorrow|tonight|right now|now|this weekend)\b|[?!.]|$)",
    re.IGNORECASE,
)

_DAYS = {"today": 0, "tomorrow": 1, "tonight": 0}


class WeatherTool(BaseTool):

    keywords = (
        "weather", "forecast", "temperature", "rain", "raining", "snow",
        "humidity", "wind", "storm", "how hot", "how cold",
    )

    ttl = 30 * 60

    @property
    def name(self) -> str:
        return "weather"

    @property
    def priority(self) -> int:
        return 100

    @property
    def description(self) -> str:
        return "Live weather conditions and short forecast (Open-Meteo)"

    @property
    def available(self) -> bool:
        # No key required - the service is free and public.
        return True

    def place_in(self, query: str) -> str | None:
        match = _PLACE_RE.search(query or "")

        if match:
            return match.group("place").strip(" .,?")

        cleaned = re.sub(
            r"\b(weather|forecast|temperature|like|going|to|be|the|in|at|for|"
            r"today|tomorrow|tonight|right now|now|is|what|how|'?s)\b",
            " ",
            (query or "").lower(),
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"[^A-Za-z .,'-]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")

        return cleaned or None

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:
        place = self.place_in(query)

        if not place:
            return []

        location = await geocode(place)

        if not location or location.get("latitude") is None:
            logger.info("Weather: could not resolve place %r", place)
            return []

        try:
            data = await fetch_json(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": ",".join(
                        (
                            "temperature_2m",
                            "apparent_temperature",
                            "relative_humidity_2m",
                            "precipitation",
                            "weather_code",
                            "wind_speed_10m",
                            "wind_direction_10m",
                        )
                    ),
                    "daily": ",".join(
                        (
                            "temperature_2m_max",
                            "temperature_2m_min",
                            "precipitation_probability_max",
                            "weather_code",
                            "sunrise",
                            "sunset",
                        )
                    ),
                    "timezone": location.get("timezone") or "auto",
                    "forecast_days": 3,
                },
                timeout=12,
            )
        except (FetchError, Exception) as error:  # noqa: BLE001 - tool contract
            logger.warning("Weather lookup failed: %s", error)
            raise

        lines = self._render(location, data, query)

        title = f"{location['name']} weather"

        if location.get("admin"):
            title += f", {location['admin']}"

        result = SearchResult(
            title=title,
            content=lines,
            source="Open-Meteo",
            url=(
                "https://api.open-meteo.com/v1/forecast?"
                f"latitude={location['latitude']}&longitude={location['longitude']}"
            ),
            confidence=0.99,
            published=data.get("current", {}).get("time"),
            category="weather",
            metadata={"location": location, "raw_current": data.get("current")},
        )

        result.stamp(tool=self.name)

        return [result]

    def _render(self, location: dict, data: dict, query: str) -> str:
        current = data.get("current") or {}
        daily = data.get("daily") or {}
        times = daily.get("time") or []

        where = location["name"]

        if location.get("country"):
            where += f", {location['country']}"

        observed = current.get("time") or now_utc().isoformat(timespec="minutes")

        lines = [
            f"Live weather for {where} (coordinates "
            f"{location['latitude']:.2f}, {location['longitude']:.2f}).",
            f"Reported at: {observed} ({data.get('timezone_abbreviation') or data.get('timezone')})",
            "",
            f"- Condition: {WMO.get(current.get('weather_code'), 'unknown')}",
            f"- Temperature: {current.get('temperature_2m')} °C "
            f"(feels like {current.get('apparent_temperature')} °C)",
            f"- Humidity: {current.get('relative_humidity_2m')}%",
            f"- Wind: {current.get('wind_speed_10m')} km/h",
            f"- Precipitation right now: {current.get('precipitation')} mm",
            "",
            "Next days:",
        ]

        for index, day in enumerate(times[:3]):
            lines.append(
                f"- {day}: {daily['temperature_2m_min'][index]}-"
                f"{daily['temperature_2m_max'][index]} °C, "
                f"{WMO.get((daily.get('weather_code') or [None]*3)[index], 'unknown')}, "
                f"{(daily.get('precipitation_probability_max') or [None]*3)[index]}% "
                "chance of rain"
            )

        asked = (query or "").lower()

        for word, offset in _DAYS.items():
            if word in asked and offset < len(times) and offset < 3:
                lines.append(
                    f"\nFor '{word}' ({times[offset]}): expect "
                    f"{WMO.get((daily.get('weather_code') or [])[offset], 'unknown')} with "
                    f"{(daily.get('precipitation_probability_max') or [])[offset]}% rain chance."
                )
                break

        return truncate("\n".join(lines), 2200)


weather = WeatherTool()

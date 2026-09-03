"""
Project Nexus

Time Tool

Current time anywhere in the world, computed with the IANA tz database that
ships with Python. No API key, no third-party rate limits, exact arithmetic -
the sort of question where an LLM guessing is unacceptable.
"""

import re
from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo, available_timezones, ZoneInfoNotFoundError

from search.search_result import SearchResult
from tools._geo import geocode
from tools.base import BaseTool
from utils.logger import logger
from utils.time_utils import UTC

_OFFSET_RE = re.compile(
    r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b|\b(\d{1,2})\s*(am|pm)\b|\b(\d{1,2})(?:\s*(am|pm))?\s*(?:hours?|hrs?)?\s*(?:from now|later)\b",
    re.IGNORECASE,
)

_CITY_RE = re.compile(
    r"\btime\s+(?:in|at|for)\s+([A-Za-z .,'-]{2,40}?)"
    r"(?:\s+(?:right now|now|today|tomorrow)\b|[?!.]|$)",
    re.IGNORECASE,
)

ALIASES = {
    "india": "Asia/Kolkata",
    "istanbul": "Europe/Istanbul",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "dubai": "Asia/Dubai",
    "tokyo": "Asia/Tokyo",
    "sydney": "Australia/Sydney",
    "utc": "UTC",
    "gmt": "UTC",
}


class TimeTool(BaseTool):

    keywords = ("time", "clock", "what time", "timezone", "time zone", "date")

    ttl = 60

    @property
    def name(self) -> str:
        return "time"

    @property
    def priority(self) -> int:
        return 100

    @property
    def description(self) -> str:
        return "Exact current date and time for any place or zone"

    async def execute(self, query: str) -> List[SearchResult]:
        text = (query or "").strip()

        # Guard: this tool must not answer non-time questions, or a background
        # refresh can file a clock reading as the answer to something else.
        if not re.search(r"\b(time|clock|date|day is it|tz|timezone)\b", text, re.IGNORECASE):
            return []

        place = None

        city = _CITY_RE.search(text)

        if city:
            place = city.group(1).strip(" .,?")

        if place is None:
            alias_hit = ALIASES.get(text.lower().strip(" ?!. "))

            place = text.strip(" ?!. ") if alias_hit else ""

        zone_id = ALIASES.get(place.lower())

        if not zone_id:
            # Try a direct IANA match such as "Asia/Kolkata".
            candidate = place.strip().replace(" ", "_")

            if "/" in candidate and candidate in available_timezones():
                zone_id = candidate

        if not zone_id:
            location = await geocode(place)

            if location and location.get("timezone"):
                zone_id = location["timezone"]
                place = location["name"]

        if not zone_id:
            if place:
                # A named place we cannot resolve must not quietly become UTC.
                logger.info("Time: could not resolve place %r", place)

                return []

            zone_id = "UTC"

        try:
            zone = ZoneInfo(zone_id)
        except (ZoneInfoNotFoundError, ValueError):
            zone = ZoneInfo("UTC")

        local = datetime.now(zone)

        lines = [
            f"Current time in {place or 'UTC'}: {local.strftime('%I:%M %p')} "
            f"({local.strftime('%A, %d %B %Y')}) — {zone_id}, "
            f"UTC{local.strftime('%z')[:3]}",
            f"Same moment in UTC: {datetime.now(ZoneInfo('UTC')).strftime('%H:%M:%S UTC, %A %d %B %Y')}",
            f"ISO-8601: {local.isoformat(timespec='seconds')}",
        ]

        offset = _OFFSET_RE.search(text)

        if offset:
            lines.append(
                "(The answer above is the current time; any offset the user "
                "asked about must be applied to that value, not guessed.)"
            )

        result = SearchResult(
            title=f"Current time — {place or 'UTC'}",
            content="\n".join(lines),
            source="IANA Time Zone Database",
            confidence=1.0,
            published=local.isoformat(timespec="seconds"),
            category="time",
            metadata={"timezone": zone_id, "iso": local.isoformat()},
        )

        result.stamp(tool=self.name)

        return [result]


time_tool = TimeTool()

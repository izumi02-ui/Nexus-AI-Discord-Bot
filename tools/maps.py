"""
Project Nexus

Maps Tool

Place lookup from OpenStreetMap Nominatim (free, no key). Returns coordinates,
the full display address and a link a human can open - never a guessed
landmark detail.
"""

import re
from typing import List
from urllib.parse import quote_plus

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json
from tools.base import BaseTool
from utils.logger import logger

PLACE_RE = re.compile(
    r"\b(?:map|maps|location|locate|where is|where's|directions to|route to|"
    r"address of|near|nearby)\s+(?:me\s+)?(?:the\s+)?([A-Za-z0-9 .,'-]{3,80}?)"
    r"(?:\s+(?:near me|map|location|address)\b|[?!.]|$)",
    re.IGNORECASE,
)


class MapsTool(BaseTool):

    keywords = ("map", "maps", "location", "where", "address", "directions", "nearby")

    searchable = False
    ttl = 24 * 3600

    @property
    def name(self) -> str:
        return "maps"

    @property
    def priority(self) -> int:
        return 99

    @property
    def description(self) -> str:
        return "Place lookup, coordinates and street address (OpenStreetMap)"

    def place_in(self, query: str) -> str:
        match = PLACE_RE.search(query or "")

        if match:
            return match.group(1).strip(" .,?")

        return re.sub(
            r"\b(please|show me|find|open|map of|maps of|locate|near me)\b",
            " ",
            (query or "").strip(),
            flags=re.IGNORECASE,
        ).strip(" ?!.") or (query or "").strip()

    async def execute(self, query: str) -> List[SearchResult]:
        place = self.place_in(query)

        if not place or len(place) < 3:
            return []

        try:
            data = await fetch_json(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": place,
                    "format": "jsonv2",
                    "limit": 3,
                    "addressdetails": 1,
                },
                headers={"Accept": "application/json"},
                timeout=12,
            )
        except FetchError as error:
            logger.warning("Maps lookup failed: %s", error)
            raise

        if not isinstance(data, list) or not data:
            return []

        lines = [f"Places matching “{place}” from OpenStreetMap:"]

        for index, hit in enumerate(data, start=1):
            address = hit.get("address") or {}
            lat, lon = hit.get("lat"), hit.get("lon")

            lines.append(
                f"\n{index}. {hit.get('display_name', 'unnamed')}"
                f"\n   type: {hit.get('category', '?')}/{hit.get('type', '?')}"
                + (f"\n   coordinates: {lat}, {lon}" if lat and lon else "")
                + (
                    f"\n   open in maps: "
                    f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"
                    if lat and lon
                    else ""
                )
                + (
                    f"\n   map of the wider area: "
                    f"https://www.google.com/maps/search/{quote_plus(place)}"
                    if index == 1
                    else ""
                )
            )

            if address:
                lines.append(
                    "   structured: "
                    + ", ".join(
                        str(address[key])
                        for key in (
                            "road",
                            "city",
                            "state",
                            "postcode",
                            "country",
                        )
                        if address.get(key)
                    )
                )

        first = data[0]

        result = SearchResult(
            title=f"{first.get('display_name', place).split(',')[0]} — map",
            content="\n".join(lines),
            source="OpenStreetMap",
            url=(
                "https://www.openstreetmap.org/search?"
                + f"query={quote_plus(place)}"
            ),
            confidence=0.97,
            category="location",
            metadata={
                "latitude": first.get("lat"),
                "longitude": first.get("lon"),
                "count": len(data),
            },
        )

        result.stamp(tool=self.name)

        return [result]


maps = MapsTool()

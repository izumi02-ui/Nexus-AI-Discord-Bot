"""
Project Nexus

Geocoding helper

Weather, time and maps questions all start with "which place does the user
mean?". One resolver, two public sources, so a tool never guesses coordinates
on its own.
"""

import asyncio

from tools._http import FetchError, fetch_json
from utils.logger import logger

_CACHE: dict[str, dict | None] = {}


async def _open_meteo(name: str) -> dict | None:
    data = await fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": name, "count": 1, "language": "en", "format": "json"},
        timeout=10,
        retries=0,
    )

    results = (data or {}).get("results") or []

    if not results:
        return None

    hit = results[0]

    return {
        "name": hit.get("name") or name,
        "admin": hit.get("admin1"),
        "country": hit.get("country"),
        "country_code": hit.get("country_code"),
        "latitude": hit.get("latitude"),
        "longitude": hit.get("longitude"),
        "timezone": hit.get("timezone"),
        "population": hit.get("population"),
        "source": "Open-Meteo Geocoding",
    }


async def _nominatim(name: str) -> dict | None:
    data = await fetch_json(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": name,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
            "extratags": 1,
        },
        headers={"Accept": "application/json"},
        timeout=10,
        retries=0,
    )

    if not isinstance(data, list) or not data:
        return None

    hit = data[0]
    address = hit.get("address") or {}

    return {
        "name": hit.get("display_name", name).split(",")[0],
        "display_name": hit.get("display_name"),
        "admin": address.get("state") or address.get("city"),
        "country": address.get("country"),
        "country_code": (address.get("country_code") or "").upper(),
        "latitude": float(hit["lat"]) if hit.get("lat") else None,
        "longitude": float(hit["lon"]) if hit.get("lon") else None,
        "timezone": (hit.get("extratags") or {}).get("timezone"),
        "osm_type": hit.get("type"),
        "source": "OpenStreetMap Nominatim",
    }


async def geocode(place: str) -> dict | None:
    """Resolve a place name into coordinates. Returns None if unknown."""
    key = (place or "").strip().lower()

    if not key:
        return None

    if key in _CACHE:
        return _CACHE[key]

    resolved = None

    for fetcher in (_open_meteo, _nominatim):
        try:
            resolved = await fetcher(key)
        except asyncio.TimeoutError:
            resolved = None
        except FetchError as error:
            logger.debug("Geocoding via %s failed: %s", fetcher.__name__, error)
            resolved = None

        if resolved:
            break

    # Remember failures too - they are expensive and rarely transient.
    _CACHE[key] = resolved

    return resolved

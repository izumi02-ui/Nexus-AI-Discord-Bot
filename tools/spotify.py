"""
Project Nexus

Spotify Tool

Track/album/artist lookup through the Spotify Web API client-credentials flow.
Needs SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET; without them the tool is
unavailable and the aggregator skips it.
"""

import asyncio
import base64
import time
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch, fetch_json
from tools.base import BaseTool
from utils.logger import logger
from utils.settings import settings

_TOKEN = {"value": None, "expires_at": 0.0}
_LOCK = asyncio.Lock()


class SpotifyTool(BaseTool):

    keywords = ("spotify", "song", "album", "artist", "playlist", "track")

    searchable = True
    required_keys = ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET")
    ttl = 7 * 24 * 3600

    @property
    def name(self) -> str:
        return "spotify"

    @property
    def priority(self) -> int:
        return 96

    @property
    def description(self) -> str:
        return "Spotify tracks, albums and artists"

    @property
    def available(self) -> bool:
        return bool(
            settings.spotify_client_id and settings.spotify_client_secret
        )

    async def token(self) -> str | None:
        async with _LOCK:
            if _TOKEN["value"] and time.time() < _TOKEN["expires_at"] - 30:
                return _TOKEN["value"]

            credentials = base64.b64encode(
                f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
            ).decode()

            try:
                response = await fetch(
                    "https://accounts.spotify.com/api/token",
                    method="post",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    params={"grant_type": "client_credentials"},
                    timeout=12,
                )
            except FetchError as error:
                logger.warning("Spotify auth failed: %s", error)
                return None

            payload = response.json()

            _TOKEN["value"] = payload.get("access_token")
            _TOKEN["expires_at"] = time.time() + int(payload.get("expires_in", 3600))

            return _TOKEN["value"]

    async def execute(self, query: str) -> List[SearchResult]:
        import re

        text = re.sub(
            r"\b(spotify|search|look up|song|track|album|artist)\b", " ",
            (query or ""), flags=re.IGNORECASE,
        )
        text = re.sub(r"\s+", " ", text).strip(" ?!.")

        if not text:
            return []

        token = await self.token()

        if not token:
            return []

        try:
            data = await fetch_json(
                "https://api.spotify.com/v1/search",
                params={"q": text, "type": "track,album,artist", "limit": 5},
                headers={"Authorization": f"Bearer {token}"},
                timeout=12,
            )
        except FetchError as error:
            logger.warning("Spotify search failed: %s", error)
            raise

        results: List[SearchResult] = []

        for kind in ("track", "album", "artist"):
            items = ((data or {}).get(kind) or {}).get("items") or []

            for item in items[:3]:
                if not item:
                    continue

                name = item.get("name", "unknown")
                external = (item.get("external_urls") or {}).get("spotify")

                if kind == "track":
                    artists = ", ".join(
                        artist.get("name", "?")
                        for artist in item.get("artists", [])
                    )
                    album = (item.get("album") or {}).get("name")
                    content = f"Track “{name}” by {artists or 'unknown artist'}"
                    if album:
                        content += f", from the album “{album}”"
                    if item.get("explicit"):
                        content += " (explicit)"
                elif kind == "album":
                    artists = ", ".join(
                        artist.get("name", "?")
                        for artist in item.get("artists", [])
                    )
                    content = (
                        f"Album “{name}” by {artists or 'unknown'}; "
                        f"released {item.get('release_date', 'unknown')}; "
                        f"{item.get('total_tracks', '?')} tracks"
                    )
                else:
                    content = (
                        f"Artist “{name}” with "
                        f"{(item.get('followers') or {}).get('total', '?')} followers"
                        + (
                            "; genres: " + ", ".join(item.get("genres", [])[:5])
                            if item.get("genres") else ""
                        )
                    )

                result = SearchResult(
                    title=f"{kind.title()}: {name}",
                    content=content,
                    source="Spotify",
                    url=external,
                    confidence=0.95,
                    category="music",
                    metadata={"spotify_id": item.get("id"), "kind": kind},
                )

                result.stamp(tool=self.name)

                results.append(result)

        return results


spotify = SpotifyTool()

"""
Project Nexus

Spotify Tool

Track/album/artist lookup through the Spotify Web API client-credentials flow.
Needs SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET; without them the tool is
unavailable and the aggregator skips it.
"""

import asyncio
import base64
import re
import time
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json
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

    @staticmethod
    def clean_query(query: str) -> str:
        """Remove request wording without deleting words inside a song title."""
        text = (query or "").strip()
        text = re.sub(
            r"^\s*(?:please\s+)?(?:give|send|show)\s+me\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(?:find|search(?:\s+for)?|look\s*up|play)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s+(?:from|on|in)\s+spotify\s*$|^\s*spotify\s*[:\-]?\s*",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s+(?:(?:song|track|album|artist|playlist)\s+)?"
            r"(?:link|url)\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s+(?:song|track|album|artist|playlist)\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return re.sub(r"\s+", " ", text).strip(" ?!.-")

    async def token(self) -> str | None:
        async with _LOCK:
            if _TOKEN["value"] and time.time() < _TOKEN["expires_at"] - 30:
                return _TOKEN["value"]

            credentials = base64.b64encode(
                f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
            ).decode()

            try:
                payload = await fetch_json(
                    "https://accounts.spotify.com/api/token",
                    method="post",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data_body={"grant_type": "client_credentials"},
                    timeout=12,
                )
            except FetchError as error:
                logger.warning("Spotify auth failed: %s", error)
                raise

            _TOKEN["value"] = payload.get("access_token")
            _TOKEN["expires_at"] = time.time() + int(payload.get("expires_in", 3600))

            if not _TOKEN["value"]:
                raise FetchError("Spotify OAuth response did not include an access token.")

            return _TOKEN["value"]

    async def execute(self, query: str) -> List[SearchResult]:
        text = self.clean_query(query)

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

        for kind, container in (
            ("track", "tracks"),
            ("album", "albums"),
            ("artist", "artists"),
        ):
            items = ((data or {}).get(container) or {}).get("items") or []

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

                image_rows = (
                    (item.get("album") or {}).get("images")
                    if kind == "track"
                    else item.get("images")
                ) or []
                image = next(
                    (
                        row.get("url")
                        for row in image_rows
                        if isinstance(row, dict) and row.get("url")
                    ),
                    None,
                )

                result = SearchResult(
                    title=f"{kind.title()}: {name}",
                    content=content,
                    source="Spotify",
                    url=external,
                    image=image,
                    confidence=0.95,
                    category="music",
                    metadata={"spotify_id": item.get("id"), "kind": kind},
                )

                result.stamp(tool=self.name)

                results.append(result)

        return results


spotify = SpotifyTool()

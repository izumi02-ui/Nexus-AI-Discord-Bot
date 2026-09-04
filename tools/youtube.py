"""
Project Nexus

YouTube Tool

Video search through the official YouTube Data API when a key is configured.
Without a key the tool is *unavailable*, so the search pipeline skips it -
instead of inventing a video title, which is exactly what the placeholder
version used to invite.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger
from utils.settings import settings


class YouTubeTool(BaseTool):

    keywords = (
        "youtube", "video", "tutorial", "trailer", "watch", "music video",
        "livestream", "live stream",
    )

    searchable = True
    required_keys = ("YOUTUBE_API_KEY",)
    ttl = 24 * 3600

    @property
    def name(self) -> str:
        return "youtube"

    @property
    def priority(self) -> int:
        return 92

    @property
    def description(self) -> str:
        return "YouTube video search (titles, channels, upload dates)"

    @property
    def available(self) -> bool:
        return bool(settings.youtube_api_key)

    @staticmethod
    def _human_time(published: str | None) -> str | None:
        from utils.time_utils import  parse_datetime

        stamp = parse_datetime(published)

        return stamp.isoformat(timespec="seconds") if stamp else None

    @staticmethod
    def clean_query(query: str) -> str:
        """Extract the requested title while preserving title words like 'Me'."""
        text = (query or "").strip()
        text = re.sub(
            r"^\s*(?:please\s+)?(?:give|send|show)\s+me\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(?:find|search(?:\s+for)?|look\s*up|play|watch)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s+(?:from|on|in)\s+(?:youtube|yt)\s*$|"
            r"^\s*(?:youtube|yt)\s*[:\-]?\s*",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s+(?:(?:video|song|track|trailer)\s+)?(?:link|url)\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return re.sub(r"\s+", " ", text).strip(" ?!.-")

    async def execute(self, query: str) -> List[SearchResult]:
        text = self.clean_query(query)

        if not text:
            return []

        try:
            data = await fetch_json(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": text,
                    "type": "video",
                    "maxResults": 5,
                    "safeSearch": "moderate",
                    "relevanceLanguage": "en",
                    "order": "relevance",
                    "key": settings.youtube_api_key,
                },
                timeout=12,
            )
        except FetchError as error:
            logger.warning("YouTube search failed: %s", error)
            raise

        ids = [
            item.get("id", {}).get("videoId")
            for item in (data or {}).get("items", [])
            if item.get("id", {}).get("videoId")
        ]

        stats = {}

        if ids:
            try:
                details = await fetch_json(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "part": "statistics,contentDetails",
                        "id": ",".join(ids),
                        "key": settings.youtube_api_key,
                    },
                    timeout=12,
                    retries=0,
                )

                stats = {
                    item["id"]: item
                    for item in (details or {}).get("items", [])
                }
            except Exception:  # noqa: BLE001 - stats are optional
                stats = {}

        results: List[SearchResult] = []

        for item in (data or {}).get("items", []):
            snippet = item.get("snippet") or {}
            video_id = (item.get("id") or {}).get("videoId")

            if not video_id:
                continue

            extra = stats.get(video_id, {})
            counts = extra.get("statistics") or {}

            published = self._human_time(snippet.get("publishedAt"))

            result = SearchResult(
                title=truncate(snippet.get("title", ""), 200),
                content=truncate(
                    "\n".join(
                        part
                        for part in (
                            f"Channel: {snippet.get('channelTitle')}"
                            if snippet.get("channelTitle") else None,
                            snippet.get("description"),
                            (
                                f"Views: {counts['viewCount']}, "
                                f"likes: {counts.get('likeCount', 'n/a')}"
                            ) if counts else None,
                            f"Length: {extra.get('contentDetails', {}).get('duration')}"
                            if extra.get("contentDetails") else None,
                        )
                        if part
                    ),
                    1200,
                ),
                source="YouTube",
                url=f"https://www.youtube.com/watch?v={video_id}",
                thumbnail=(snippet.get("thumbnails", {}).get("medium", {}) or {}).get("url"),
                video=f"https://www.youtube.com/embed/{video_id}",
                published=published,
                author=snippet.get("channelTitle"),
                confidence=0.86,
                category="video",
                metadata={"video_id": video_id, "view_count": counts.get("viewCount")},
            )

            result.stamp(tool=self.name)

            results.append(result)

        return results


youtube = YouTubeTool()

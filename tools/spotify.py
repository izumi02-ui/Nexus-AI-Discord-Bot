"""
Project Nexus

Spotify Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class SpotifyTool(BaseTool):

    @property
    def name(self) -> str:

        return "spotify"

    @property
    def priority(self) -> int:

        return 96

    @property
    def description(self) -> str:

        return "Spotify Music Information"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Spotify Search: {query}"
        )

        # =====================================
        # Future Features
        # =====================================

        # Search Tracks
        # Search Albums
        # Search Artists
        # Search Playlists
        # Album Information
        # Artist Information
        # Genres
        # Popular Tracks
        # Release Dates
        # Audio Features
        # Recommendations
        # Podcast Search
        # Episode Search

        return [

            SearchResult(

                title="Spotify",

                content="Spotify integration is under development.",

                source="Spotify",

                confidence=0.96,

            )

        ]


spotify = SpotifyTool()

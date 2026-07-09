"""
Project Nexus

YouTube Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class YouTubeTool(BaseTool):

    @property
    def name(self) -> str:

        return "youtube"

    @property
    def priority(self) -> int:

        return 92

    @property
    def description(self) -> str:

        return "YouTube Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"YouTube Search: {query}"
        )

        # TODO:
        # YouTube Data API v3

        return [

            SearchResult(

                title="YouTube",

                content="YouTube integration is under development.",

                source="YouTube",

                confidence=0.90,

            )

        ]


youtube = YouTubeTool()

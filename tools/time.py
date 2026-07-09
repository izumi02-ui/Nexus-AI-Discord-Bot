"""
Project Nexus

Time Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class TimeTool(BaseTool):

    @property
    def name(self) -> str:

        return "time"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "World Time"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Time Search: {query}"
        )

        # TODO:
        # WorldTimeAPI
        # TimeZoneDB
        # IANA Time Zones

        return [

            SearchResult(

                title="Time",

                content="Time integration is under development.",

                source="Time",

                confidence=1.0,

            )

        ]


time_tool = TimeTool()

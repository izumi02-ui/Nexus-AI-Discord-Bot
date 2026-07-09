"""
Project Nexus

Steam Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class SteamTool(BaseTool):

    @property
    def name(self) -> str:

        return "steam"

    @property
    def priority(self) -> int:

        return 96

    @property
    def description(self) -> str:

        return "Steam Store & Game Information"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Steam Search: {query}"
        )

        # =====================================
        # Future Features
        # =====================================

        # Steam Store
        # Steam App Details
        # Steam News
        # Steam Reviews
        # Steam Achievements
        # Steam Workshop
        # Steam Charts
        # SteamDB
        # Steam Price History
        # Steam Discounts
        # Steam DLC
        # Steam Developer
        # Steam Publisher

        return [

            SearchResult(

                title="Steam",

                content="Steam integration is under development.",

                source="Steam",

                confidence=0.96,

            )

        ]


steam = SteamTool()

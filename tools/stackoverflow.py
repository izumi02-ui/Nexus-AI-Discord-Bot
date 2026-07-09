"""
Project Nexus

Stack Overflow Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class StackOverflowTool(BaseTool):

    @property
    def name(self) -> str:

        return "stackoverflow"

    @property
    def priority(self) -> int:

        return 94

    @property
    def description(self) -> str:

        return "Stack Overflow Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Stack Overflow Search: {query}"
        )

        # TODO:
        # Stack Exchange API

        return [

            SearchResult(

                title="Stack Overflow",

                content="Stack Overflow integration is under development.",

                source="Stack Overflow",

                confidence=0.94,

            )

        ]


stackoverflow = StackOverflowTool()

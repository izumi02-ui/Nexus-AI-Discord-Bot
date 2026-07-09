"""
Project Nexus

DuckDuckGo Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class DuckDuckGoTool(BaseTool):

    @property
    def name(self) -> str:

        return "duckduckgo"

    @property
    def priority(self) -> int:

        return 85

    @property
    def description(self) -> str:

        return "DuckDuckGo Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"DuckDuckGo Search: {query}"
        )

        # TODO:
        # DuckDuckGo Search API

        return [

            SearchResult(

                title="DuckDuckGo",

                content="DuckDuckGo integration is under development.",

                source="DuckDuckGo",

                confidence=0.85,

            )

        ]


duckduckgo = DuckDuckGoTool()

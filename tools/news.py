"""
Project Nexus

News Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class NewsTool(BaseTool):

    @property
    def name(self) -> str:

        return "news"

    @property
    def priority(self) -> int:

        return 98

    @property
    def description(self) -> str:

        return "News Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"News Search: {query}"
        )

        # TODO:
        # Google News
        # GNews
        # NewsAPI

        return [

            SearchResult(

                title="News",

                content="News provider is under development.",

                source="News",

                confidence=0.90,

            )

        ]


news = NewsTool()

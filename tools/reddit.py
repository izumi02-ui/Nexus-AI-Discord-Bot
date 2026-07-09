"""
Project Nexus

Reddit Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class RedditTool(BaseTool):

    @property
    def name(self) -> str:

        return "reddit"

    @property
    def priority(self) -> int:

        return 90

    @property
    def description(self) -> str:

        return "Reddit Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Reddit Search: {query}"
        )

        # TODO:
        # Reddit API / Reddit Search

        return [

            SearchResult(

                title="Reddit",

                content="Reddit integration is under development.",

                source="Reddit",

                confidence=0.80,

            )

        ]


reddit = RedditTool()

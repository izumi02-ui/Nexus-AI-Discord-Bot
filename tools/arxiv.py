"""
Project Nexus

arXiv Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class ArxivTool(BaseTool):

    @property
    def name(self) -> str:

        return "arxiv"

    @property
    def priority(self) -> int:

        return 97

    @property
    def description(self) -> str:

        return "arXiv Research Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"arXiv Search: {query}"
        )

        # TODO:
        # arXiv API

        return [

            SearchResult(

                title="arXiv",

                content="arXiv integration is under development.",

                source="arXiv",

                confidence=0.97,

            )

        ]


arxiv = ArxivTool()

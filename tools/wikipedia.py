"""
Project Nexus

Wikipedia Tool
"""

from typing import List

import wikipedia

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class WikipediaTool(BaseTool):

    @property
    def name(self) -> str:

        return "wikipedia"

    @property
    def priority(self) -> int:

        return 95

    @property
    def description(self) -> str:

        return "Wikipedia Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        try:

            wikipedia.set_lang("en")

            page = wikipedia.page(
                query,
                auto_suggest=True
            )

            summary = wikipedia.summary(
                query,
                sentences=5,
                auto_suggest=True
            )

            logger.info(
                f"Wikipedia: {query}"
            )

            return [

                SearchResult(

                    title=page.title,

                    content=summary,

                    source="Wikipedia",

                    url=page.url,

                    confidence=0.95,

                )

            ]

        except Exception as error:

            logger.warning(
                f"Wikipedia Failed: {error}"
            )

            return []


wikipedia = WikipediaTool()

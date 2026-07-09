"""
Project Nexus

Currency Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class CurrencyTool(BaseTool):

    @property
    def name(self) -> str:

        return "currency"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "Currency Exchange"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Currency Search: {query}"
        )

        # TODO:
        # ExchangeRate.host
        # Frankfurter API
        # CurrencyAPI
        # Fixer.io

        return [

            SearchResult(

                title="Currency",

                content="Currency integration is under development.",

                source="Currency",

                confidence=1.0,

            )

        ]


currency = CurrencyTool()

"""
Project Nexus

Search Aggregator

Collects results from multiple
search providers.
"""

from typing import List

from search.search_result import SearchResult

from tools.google_search import google_search
from tools.wikipedia import wikipedia
from tools.github import github
from tools.reddit import reddit
from tools.news import news

from utils.logger import logger


class SearchAggregator:

    def __init__(self):

        self.providers = [

            google_search,
            wikipedia,
            github,
            reddit,
            news,

        ]

    async def search(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Searching: {query}"
        )

        results = []

        for provider in self.providers:

            try:

                result = await provider.execute(
                    query
                )

                if result is None:
                    continue

                if isinstance(result, list):

                    results.extend(result)

                else:

                    results.append(result)

            except Exception as error:

                logger.warning(
                    f"{provider.name} failed: {error}"
                )

        return results


aggregator = SearchAggregator()

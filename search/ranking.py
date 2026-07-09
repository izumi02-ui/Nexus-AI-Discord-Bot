"""
Project Nexus

Search Ranking

Ranks search results by confidence.
"""

from typing import List

from search.search_result import SearchResult

from utils.logger import logger


class SearchRanking:

    def rank(
        self,
        results: List[SearchResult],
    ) -> List[SearchResult]:

        logger.info(
            f"Ranking {len(results)} results."
        )

        results.sort(
            key=lambda result: result.confidence,
            reverse=True
        )

        return results

    def best(
        self,
        results: List[SearchResult],
    ) -> SearchResult | None:

        if not results:

            return None

        return self.rank(results)[0]


ranking = SearchRanking()

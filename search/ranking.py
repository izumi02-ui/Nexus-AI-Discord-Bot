"""
Project Nexus

Search Ranking

Ranks, filters and deduplicates
search results.
"""

from typing import List

from search.search_result import SearchResult

from utils.logger import logger


class SearchRanking:

    SOURCE_WEIGHTS = {

        "Google": 1.00,
        "Wikipedia": 0.98,
        "GitHub": 0.97,
        "News": 0.97,
        "arXiv": 0.99,
        "Stack Overflow": 0.96,
        "YouTube": 0.92,
        "Reddit": 0.88,
        "Steam": 0.95,
        "Spotify": 0.95,
        "Maps": 0.95,
        "Weather": 1.00,
        "Currency": 1.00,
        "Time": 1.00,
        "Translator": 0.95,
        "Vision": 0.90,
        "OCR": 0.90,
        "File Reader": 1.00,
        "Web Scraper": 0.90,
        "DuckDuckGo": 0.85,

    }

    def rank(
        self,
        results: List[SearchResult],
    ) -> List[SearchResult]:

        logger.info(
            f"Ranking {len(results)} results."
        )

        filtered = []

        seen = set()

        for result in results:

            if not result.success:
                continue

            if not result.content:
                continue

            key = (
                result.title.strip().lower(),
                result.source.strip().lower(),
            )

            if key in seen:
                continue

            seen.add(key)

            weight = self.SOURCE_WEIGHTS.get(
                result.source,
                0.75,
            )

            result.confidence *= weight

            filtered.append(result)

        filtered.sort(

            key=lambda r: r.confidence,

            reverse=True,

        )

        logger.info(
            f"{len(filtered)} ranked results."
        )

        return filtered

    def best(
        self,
        results: List[SearchResult],
    ) -> SearchResult | None:

        ranked = self.rank(results)

        if not ranked:

            return None

        return ranked[0]


ranking = SearchRanking()

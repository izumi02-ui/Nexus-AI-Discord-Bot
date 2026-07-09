"""
Project Nexus

Search Aggregator

Runs multiple search providers
concurrently and merges results.
"""

import asyncio
from typing import List

from search.search_result import SearchResult
from search.ranking import ranking
from search.cache import cache

from tools.manager import tool_manager

from utils.logger import logger


class SearchAggregator:

    def __init__(self):

        logger.info(
            "Search Aggregator Ready."
        )

    async def search(
        self,
        query: str,
        tools: List[str] | None = None,
    ) -> List[SearchResult]:

        # ==========================
        # Cache
        # ==========================

        cached = cache.get(query)

        if cached is not None:

            logger.info(
                f"Cache Hit: {query}"
            )

            return cached

        # ==========================
        # Select Tools
        # ==========================

        if tools is None:

            providers = [

                tool_manager.get(name)

                for name in tool_manager.available

            ]

        else:

            providers = [

                tool_manager.get(name)

                for name in tools

            ]

        providers = [

            provider

            for provider in providers

            if provider is not None
        ]

        logger.info(
            f"Searching with {len(providers)} providers."
        )

        # ==========================
        # Execute
        # ==========================

        tasks = [

            provider.execute(query)

            for provider in providers
        ]

        responses = await asyncio.gather(

            *tasks,

            return_exceptions=True,

        )

        # ==========================
        # Merge Results
        # ==========================

        results = []

        for provider, response in zip(
            providers,
            responses,
        ):

            if isinstance(
                response,
                Exception,
            ):

                logger.warning(
                    f"{provider.name} failed: {response}"
                )

                continue

            if not response:

                continue

            results.extend(response)

        # ==========================
        # Rank
        # ==========================

        results = ranking.rank(
            results
        )

        # ==========================
        # Cache
        # ==========================

        cache.set(
            query,
            results,
        )

        logger.info(
            f"Collected {len(results)} results."
        )

        return results


aggregator = SearchAggregator()

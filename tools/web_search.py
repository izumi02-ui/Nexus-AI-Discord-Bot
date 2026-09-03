"""
Project Nexus

Provider Web Search Tool

Asks the *currently selected model provider* to ground its answer in a live
web search, which is the cheapest high-quality evidence Nexus can get:

  * Gemini  - native google_search tool
  * OpenRouter - the "web" grounding plugin (any model, incl. free ones)

Anything else the provider does not support returns no results, and the
aggregator moves on to the keyless tools.
"""

from typing import List

from search.search_result import SearchResult
from tools.base import BaseTool
from utils.logger import logger


class WebSearchTool(BaseTool):

    keywords = ("search", "web", "look up", "latest", "current", "news")

    searchable = True
    ttl = 1800

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def priority(self) -> int:
        return 98

    @property
    def description(self) -> str:
        return "Provider-native web search (Gemini / OpenRouter grounding)"

    @staticmethod
    def _manager():
        """
        Lazy import.

        tools -> ai.provider_manager -> ai.providers.base -> ai.tool_registry
        -> tools.manager is a cycle if done at module scope, and the provider
        layer is optional for everything else, so a failure here just means
        "no provider-backed search".
        """
        try:
            from ai.provider_manager import provider_manager

            return provider_manager
        except Exception as error:  # noqa: BLE001
            logger.debug("Provider manager unavailable: %s", error)

            return None

    @property
    def available(self) -> bool:
        manager = self._manager()

        provider = getattr(manager, "provider", None) if manager else None

        return bool(provider and provider.supports("web_search"))

    async def execute(self, query: str) -> List[SearchResult]:
        manager = self._manager()

        if manager is None:
            return []

        provider = manager.provider

        if not provider:
            return []

        logger.info("Provider web search via %s: %s", provider.name, query)

        try:
            content = await provider.use_tool("web_search", query)
        except NotImplementedError as error:
            logger.info("Web search unsupported: %s", error)
            return []
        except Exception as error:  # noqa: BLE001 - tool contract
            logger.warning("Provider web search failed: %s", error)
            raise

        content = str(content or "").strip()

        if not content or len(content) < 20:
            return []

        result = SearchResult(
            title=f"{provider.name} web search",
            content=content[:3000],
            source=f"{provider.name} Search",
            confidence=0.93,
            category="web",
            metadata={"grounded": True, "provider": provider.name},
        )

        result.stamp(tool=self.name)

        return [result]


web_search = WebSearchTool()

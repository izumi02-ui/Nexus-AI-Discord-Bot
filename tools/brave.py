"""
Project Nexus

Brave Search Tool

Optional paid web search for Nexus. It turns current-event questions into
grounded answers with real URLs, but it is not required: provider search,
Google grounding, DuckDuckGo and topic-specific sources remain available.

Without BRAVE_API_KEY the tool reports itself unavailable and is skipped by
the aggregator, exactly like every other keyless-degraded tool.
"""

from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger
from utils.settings import settings


class BraveSearchTool(BaseTool):

    keywords = ("search", "web", "news", "latest", "current", "who", "what")

    required_keys = ("BRAVE_API_KEY",)
    ttl = 3600

    @property
    def name(self) -> str:
        return "brave"

    @property
    def priority(self) -> int:
        return 99

    @property
    def description(self) -> str:
        return "Brave Web Search (real web results with URLs)"

    @property
    def available(self) -> bool:
        return bool(getattr(settings, "brave_api_key", None))

    async def execute(
        self,
        query: str,
        *,
        count: int = 6,
        freshness: str | None = None,
    ) -> List[SearchResult]:
        params = {"q": query, "count": min(count, 20)}

        if freshness:
            params["freshness"] = freshness

        try:
            data = await fetch_json(
                "https://api.search.brave.com/res/v1/web/search",
                params=params,
                headers={
                    "X-Subscription-Token": settings.brave_api_key,
                    "Accept": "application/json",
                },
                timeout=12,
            )
        except FetchError as error:
            logger.warning("Brave search failed: %s", error)
            raise

        results: List[SearchResult] = []

        web = (data or {}).get("web") or {}

        for item in web.get("results") or []:
            results.append(
                SearchResult(
                    title=truncate(item.get("title") or "", 200),
                    content=truncate(
                        item.get("description") or item.get("page_age") or "", 1400
                    ),
                    source="Brave Search",
                    url=item.get("url"),
                    published=item.get("page_age") or item.get("age"),
                    confidence=0.95,
                    category="web",
                    metadata={
                        "profile": (item.get("profile") or {}).get("name"),
                        "language": item.get("language"),
                    },
                ).stamp(tool=self.name)
            )

        # Brave also returns direct answers and "facts" - the most reliable
        # snippets in the payload when present.
        for key in ("answers", "locations", "videos"):
            block = web.get(key) or (data or {}).get(key) or []

            for item in list(block)[:2]:
                text = item.get("snippet") or item.get("description")
                title = item.get("title") or f"{key} result"

                if not text:
                    continue

                results.append(
                    SearchResult(
                        title=title,
                        content=truncate(text, 1200),
                        source=f"Brave Search ({key})",
                        url=item.get("url"),
                        published=item.get("page_age"),
                        confidence=0.93,
                        category="web",
                    ).stamp(tool=self.name)
                )

        return results


brave = BraveSearchTool()

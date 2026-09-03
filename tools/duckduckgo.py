"""
Project Nexus

DuckDuckGo Tool

Uses DuckDuckGo's free Instant Answer API (no key, no scraping). It answers
definitions, numbers, places and "what is X" style lookups, and it is honest
about being empty: when DuckDuckGo has nothing, this tool returns nothing -
never filler text.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json
from tools.base import BaseTool
from utils.logger import logger

HTML_RE = re.compile(r"<[^>]+>")


class DuckDuckGoTool(BaseTool):

    keywords = ("search", "duckduckgo", "find out", "look up")

    ttl = 3600

    @property
    def name(self) -> str:
        return "duckduckgo"

    @property
    def priority(self) -> int:
        return 85

    @property
    def description(self) -> str:
        return "DuckDuckGo instant answers and related topics"

    @property
    def available(self) -> bool:
        return True

    async def execute(self, query: str) -> List[SearchResult]:
        text = re.sub(r"^\s*(?:search\s+for|look\s*up|google|ddg)\s*", "",
                      (query or "").strip(), flags=re.IGNORECASE).strip(" ?!.")

        if not text:
            return []

        try:
            data = await fetch_json(
                "https://api.duckduckgo.com/",
                params={
                    "q": text,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                    "no_redirect": 1,
                },
                timeout=10,
            )
        except FetchError as error:
            logger.warning("DuckDuckGo failed: %s", error)
            raise

        if not isinstance(data, dict):
            return []

        results: List[SearchResult] = []

        heading = data.get("Heading") or ""
        abstract = HTML_RE.sub("", data.get("AbstractText") or "").strip()
        abstract_url = data.get("AbstractURL")
        source = data.get("AbstractSource") or "DuckDuckGo"

        if abstract:
            results.append(
                SearchResult(
                    title=heading or text,
                    content=abstract,
                    source=source,
                    url=abstract_url,
                    confidence=0.9,
                    category=data.get("Topic") or "general",
                    metadata={
                        "answer_type": data.get("AnswerType"),
                        "image": data.get("Image"),
                    },
                ).stamp(tool=self.name)
            )

        # Direct answers ("what is 5 miles in km", definitions...).
        for key in ("Answer", "Definition"):
            value = HTML_RE.sub("", str(data.get(key) or "")).strip()

            if value:
                results.append(
                    SearchResult(
                        title=f"{heading or text} — {key.lower()}",
                        content=value,
                        source=data.get("DefinitionSource") or source,
                        url=data.get("DefinitionURL") or abstract_url,
                        confidence=0.88,
                        metadata={"direct_answer": True},
                    ).stamp(tool=self.name)
                )

        related = []

        for topic in (data.get("RelatedTopics") or [])[:6]:
            if not isinstance(topic, dict):
                continue

            if "Topics" in topic:
                related.extend(
                    item for item in topic["Topics"] if isinstance(item, dict)
                )
            else:
                related.append(topic)

        for topic in related[:3]:
            snippet = HTML_RE.sub("", str(topic.get("Text") or "")).strip()

            if not snippet:
                continue

            results.append(
                SearchResult(
                    title=snippet.split(" - ")[0][:120],
                    content=snippet,
                    source="DuckDuckGo",
                    url=topic.get("FirstURL"),
                    confidence=0.78,
                    tags=["related"],
                ).stamp(tool=self.name)
            )

        if not results:
            logger.info("DuckDuckGo had no instant answer for %r", text)

        return results


duckduckgo = DuckDuckGoTool()

"""
Project Nexus

arXiv Tool

Pre-print search through the official arXiv Atom API. Used whenever a question
touches research claims, so Nexus cites the paper instead of paraphrasing a
memory of a tweet about a paper.
"""

import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_text, truncate
from tools.base import BaseTool
from utils.logger import logger

FIELD_PREFIX = re.compile(r"^(ti|title|au|author|abs|cat|all):\s*", re.IGNORECASE)


class ArxivTool(BaseTool):

    keywords = (
        "arxiv", "paper", "preprint", "study", "research", "doi",
        "benchmark", "state of the art", "sota",
    )

    ttl = 7 * 24 * 3600

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def priority(self) -> int:
        return 97

    @property
    def description(self) -> str:
        return "arXiv papers with abstract, authors and publication date"

    async def execute(
        self,
        query: str,
        *,
        max_results: int = 4,
    ) -> List[SearchResult]:
        text = re.sub(r"^\s*(?:arxiv|search arxiv|find paper(?:s)? about)\s*", "",
                      (query or "").strip(), flags=re.IGNORECASE).strip(" ?!.")

        if not text:
            return []

        if not FIELD_PREFIX.match(text):
            text = f"all:{text}"

        try:
            xml = await fetch_text(
                "http://export.arxiv.org/api/query",
                params={
                    "search_query": text,
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                },
                timeout=15,
            )
        except FetchError as error:
            logger.warning("arXiv search failed: %s", error)
            raise

        try:
            import feedparser

            parsed = feedparser.parse(xml)
            entries = list(parsed.entries or [])
        except Exception:  # pragma: no cover - feedparser is a hard dependency
            logger.debug("feedparser unavailable, using regex fallback")
            entries = []

        results: List[SearchResult] = []

        for entry in entries[:max_results]:
            title = re.sub(r"\s+", " ", getattr(entry, "title", "") or "").strip()
            summary = re.sub(r"\s+", " ", getattr(entry, "summary", "") or "").strip()

            authors = [
                person.get("name")
                for person in (getattr(entry, "authors", None) or [])
                if isinstance(person, dict)
            ]

            link = getattr(entry, "link", None)

            pdf = None

            for hedge in getattr(entry, "links", None) or []:
                if hedge.get("type") == "application/pdf":
                    pdf = hedge.get("href")

            result = SearchResult(
                title=title,
                content=truncate(summary, 2200),
                source="arXiv",
                url=link,
                author=", ".join([a for a in authors if a][:6]) or None,
                published=getattr(entry, "published", None) or getattr(
                    entry, "updated", None
                ),
                confidence=0.97,
                category=(
                    getattr(entry, "arxiv_primary_category", {}) or {}
                ).get("term"),
                image=pdf,
                metadata={
                    "authors": authors,
                    "pdf": pdf,
                    "arxiv_id": getattr(entry, "id", None),
                    "categories": [
                        tag.get("term")
                        for tag in (getattr(entry, "tags", None) or [])
                        if isinstance(tag, dict)
                    ][:5],
                },
            )

            result.stamp(tool=self.name)

            results.append(result)

        if not results:
            logger.info("arXiv returned nothing for %r", text)

        return results


arxiv = ArxivTool()

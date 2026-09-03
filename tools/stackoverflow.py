"""
Project Nexus

Stack Overflow Tool

Stack Exchange public API (no key needed for search). Returns real answers with
vote counts and accept status, so Nexus can say "the accepted answer says X"
rather than inventing an idiomatic fix.
"""

import html
import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger

FILTER = "withbody"  # built-in Stack Exchange filter: includes the HTML body

TAG_RE = re.compile(r"\b([a-z][a-z0-9+#.\-]{1,25})\b")


class StackOverflowTool(BaseTool):

    keywords = (
        "stackoverflow", "stack overflow", "error", "exception", "traceback",
        "python", "javascript", "typescript", "java", "c++", "rust", "go",
        "bug", "segfault",
    )

    searchable = True
    ttl = 12 * 3600

    @property
    def name(self) -> str:
        return "stackoverflow"

    @property
    def priority(self) -> int:
        return 94

    @property
    def description(self) -> str:
        return "Stack Overflow questions and accepted answers"

    async def _query(self, text: str, *, accepted: bool) -> dict:
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": text,
            "site": "stackoverflow",
            "pagesize": 5,
            "answers": 1,
            "filter": FILTER,
        }

        if accepted:
            params["accepted"] = "True"

        return await fetch_json(
            "https://api.stackexchange.com/2.3/search/advanced",
            params=params,
            timeout=12,
        )

    async def execute(self, query: str) -> List[SearchResult]:
        text = re.sub(r"\b(stack\s?overflow|error|exception|issue)\b", " ",
                      (query or ""), flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" ?!.")

        if not text:
            text = (query or "").strip()

        try:
            data = await self._query(text, accepted=True)

            if not (data or {}).get("items"):
                data = await self._query(text, accepted=False)
        except FetchError as error:
            logger.warning("Stack Overflow search failed: %s", error)
            raise

        items = (data or {}).get("items") or []

        results = []

        for item in items:
            title = html.unescape(item.get("title", ""))
            body = html.unescape(re.sub(r"<[^>]+>", " ", item.get("body", "") or ""))
            link = item.get("link")

            result = SearchResult(
                title=title,
                content=truncate(body, 1600),
                source="Stack Overflow",
                url=link,
                published=item.get("creation_date"),
                confidence=0.9
                + (0.03 * min(int(item.get("score", 0)), 3)),
                category="programming",
                metadata={
                    "score": item.get("score"),
                    "answer_count": item.get("answer_count"),
                    "is_accepted": item.get("is_answered"),
                    "tags": item.get("tags", [])[:6],
                    "views": item.get("view_count"),
                },
                tags=item.get("tags", [])[:6],
            )

            result.stamp(tool=self.name)

            results.append(result)

        return results[:4]


stackoverflow = StackOverflowTool()

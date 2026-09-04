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

    async def _answers(self, question_ids: list[int]) -> dict[int, dict]:
        """Fetch the accepted (or highest-voted) answer for each question."""
        if not question_ids:
            return {}

        data = await fetch_json(
            "https://api.stackexchange.com/2.3/questions/"
            + ";".join(str(question_id) for question_id in question_ids)
            + "/answers",
            params={
                "order": "desc",
                "sort": "votes",
                "site": "stackoverflow",
                "pagesize": 20,
                "filter": FILTER,
            },
            timeout=12,
        )

        selected: dict[int, dict] = {}

        for answer in (data or {}).get("items") or []:
            question_id = answer.get("question_id")

            if question_id is None:
                continue

            existing = selected.get(question_id)

            if existing is None or (
                answer.get("is_accepted") and not existing.get("is_accepted")
            ):
                selected[question_id] = answer

        return selected

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
        question_ids = [
            item.get("question_id")
            for item in items
            if item.get("question_id") is not None
        ]

        try:
            answers = await self._answers(question_ids)
        except FetchError as error:
            # The question snippets are still useful evidence when the second
            # endpoint is rate-limited, so degrade without inventing an answer.
            logger.info("Stack Overflow answer lookup failed: %s", error)
            answers = {}

        results = []

        for item in items:
            title = html.unescape(item.get("title", ""))
            answer = answers.get(item.get("question_id"))
            raw_body = (answer or item).get("body", "") or ""
            body = html.unescape(re.sub(r"<[^>]+>", " ", raw_body))
            body = re.sub(r"\s+", " ", body).strip()
            link = item.get("link")

            if answer:
                label = "Accepted answer" if answer.get("is_accepted") else "Top-voted answer"
                content = f"{label}: {body}"
            else:
                content = f"Question excerpt (answer endpoint unavailable): {body}"

            result = SearchResult(
                title=title,
                content=truncate(content, 1600),
                source="Stack Overflow",
                url=link,
                published=item.get("creation_date"),
                confidence=0.9
                + (0.03 * min(int(item.get("score", 0)), 3)),
                category="programming",
                metadata={
                    "question_score": item.get("score"),
                    "answer_score": (answer or {}).get("score"),
                    "answer_count": item.get("answer_count"),
                    "is_accepted": bool((answer or {}).get("is_accepted")),
                    "question_id": item.get("question_id"),
                    "answer_id": (answer or {}).get("answer_id"),
                    "tags": item.get("tags", [])[:6],
                    "views": item.get("view_count"),
                },
                tags=item.get("tags", [])[:6],
            )

            result.stamp(tool=self.name)

            results.append(result)

        return results[:4]


stackoverflow = StackOverflowTool()

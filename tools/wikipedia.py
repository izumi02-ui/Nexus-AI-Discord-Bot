"""
Project Nexus

Wikipedia Tool

Talks to the official Wikipedia REST API instead of the unmaintained
``wikipedia`` scraper package.

Why it matters for accuracy: the old implementation used ``auto_suggest=True``
and pulled a 5-sentence summary of whatever page the API *thought* the user
meant. A query about a person's 2026 status could silently return a 2019
snapshot of a similarly named article. Here the search is explicit, the best
match is chosen by title overlap, and every result carries the revision
timestamp so stale pages can be discounted.
"""

import re
from typing import List
from urllib.parse import quote

from search.search_result import SearchResult
from tools._http import FetchError, fetch_json, truncate
from tools.base import BaseTool
from utils.logger import logger
from utils.time_utils import humanize_age

BASE = "https://en.wikipedia.org"

LEAD_SENTENCES = 8


class WikipediaTool(BaseTool):

    keywords = ("wikipedia", "wiki", "who is", "what is", "biography", "history of")

    ttl = 6 * 3600

    @property
    def name(self) -> str:
        return "wikipedia"

    @property
    def priority(self) -> int:
        return 95

    @property
    def description(self) -> str:
        return "Wikipedia summaries with the exact page and revision used"

    def clean_query(self, query: str) -> str:
        text = re.sub(
            r"^\s*(?:wikipedia|wiki)\s*(?:for|about|search)?\s*",
            "",
            (query or "").strip(),
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(?:who (?:is|was)|what (?:is|was|are)|tell me about)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        return text.strip(" ?!.") or (query or "").strip()

    async def execute(self, query: str) -> List[SearchResult]:
        subject = self.clean_query(query)

        if not subject:
            return []

        try:
            hits = await self._search(subject)
        except FetchError as error:
            logger.warning("Wikipedia search failed: %s", error)
            raise

        if not hits:
            return []

        results: List[SearchResult] = []

        for page in hits[:3]:
            key = page.get("key") or page.get("title", "").replace(" ", "_")

            if not key:
                continue

            try:
                summary = await fetch_json(
                    f"{BASE}/api/rest_v1/page/summary/{quote(str(key), safe='')}",
                    timeout=10,
                    retries=0,
                )
            except Exception as error:  # noqa: BLE001
                logger.debug("Wikipedia summary failed for %s: %s", key, error)
                continue

            if not summary or summary.get("type") == "disambiguation":
                results.append(
                    SearchResult(
                        title=f"{summary.get('title', key)} (disambiguation)",
                        content=(
                            "The title is ambiguous on Wikipedia. "
                            + (summary.get("extract") or "")
                        ),
                        source="Wikipedia",
                        url=(summary.get("content_urls") or {})
                        .get("desktop", {})
                        .get("page"),
                        confidence=0.5,
                        category="disambiguation",
                    ).stamp(tool=self.name)
                )
                continue

            extract = summary.get("extract") or page.get("excerpt") or ""

            if not extract:
                continue

            revision = (summary.get("timestamp")
                        or page.get("timestamp"))

            url = (
                (summary.get("content_urls") or {}).get("desktop", {}).get("page")
                or f"{BASE}/wiki/{quote(str(key), safe='')}"
            )

            result = SearchResult(
                title=summary.get("title") or page.get("title") or key,
                content=self._clip(extract),
                source="Wikipedia",
                url=url,
                confidence=0.94,
                published=revision,
                language=summary.get("lang", "en"),
                category="encyclopedia",
                thumbnail=(summary.get("thumbnail") or {}).get("source"),
                metadata={
                    "description": summary.get("description"),
                    "revision": revision,
                    "revision_age": humanize_age(revision) if revision else None,
                    "thumbnail": (summary.get("thumbnail") or {}).get("source"),
                },
            )

            result.stamp(tool=self.name)

            results.append(result)

        return results

    def _clip(self, extract: str) -> str:
        """Keep the lead section, capped by sentences so quoting stays safe."""
        extract = re.sub(r"\s+", " ", extract).strip()

        sentences = re.split(r"(?<=[.!?])\s+", extract)

        return truncate(" ".join(sentences[:LEAD_SENTENCES]), 2000)

    async def _search(self, subject: str) -> list[dict]:
        data = await fetch_json(
            f"{BASE}/w/rest.php/v1/search/page",
            params={"q": subject, "limit": 5},
            timeout=12,
        )

        pages = (data or {}).get("pages") or []

        if not pages:
            data = await fetch_json(
                f"{BASE}/w/api.php",
                params={
                    "action": "opensearch",
                    "search": subject,
                    "limit": 5,
                    "namespace": 0,
                    "format": "json",
                    "suggestion": "true",
                },
                timeout=10,
            )

            if isinstance(data, list) and len(data) >= 4:
                _, titles, descriptions, suggestions = data[:4]

                pages = [
                    {
                        "key": title.replace(" ", "_"),
                        "title": title,
                        "excerpt": description,
                        "matched_title": suggestion or None,
                    }
                    for title, description, suggestion in zip(
                        titles,
                        descriptions,
                        (suggestions or []) + [None] * len(titles),
                    )
                ]

        wanted = {
            word
            for word in re.findall(r"[a-z0-9]+", subject.lower())
            if len(word) > 2
        }

        def relevance(page: dict) -> float:
            title = re.sub(r"[^a-z0-9]+", " ", str(page.get("title", "")).lower())
            score = len(wanted & set(title.split()))

            if wanted and title.strip() == " ".join(sorted(wanted)):
                score += 3

            if page.get("matched_title"):
                score += 1

            return float(score)

        return sorted(pages, key=relevance, reverse=True)


wikipedia = WikipediaTool()

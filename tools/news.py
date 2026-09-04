"""
Project Nexus

News Tool

Headlines and article summaries from publishers' own public RSS feeds, plus
NewsAPI / GNews when a key is configured.

Deliberately does NOT scrape a search engine's news tab: the feeds below are
published by the outlets for redistribution, and each item keeps its own
publish date so the freshness rules can judge it.
"""

import asyncio
import os
import re
from typing import List

from search.search_result import SearchResult
from tools._http import FetchError, fetch_text, fetch_json, html_to_text, truncate
from tools.base import BaseTool
from utils.logger import logger

FEEDS = {
    "world": [
        ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("NPR", "https://feeds.npr.org/1001/rss.xml"),
        ("The Guardian", "https://www.theguardian.com/world/rss"),
    ],
    "technology": [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("Hacker News", "https://hnrss.org/frontpage"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
    ],
    "science": [
        ("Nature", "https://www.nature.com/nature.rss"),
        ("ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml"),
        ("Space.com", "https://www.space.com/feeds/all"),
        ("NASA", "https://www.nasa.gov/feed/"),
    ],
}

SECTION_RE = re.compile(
    r"\b(technology|tech|science|business|sports?|politics|world|health|"
    r"climate|space|ai)\b",
    re.IGNORECASE,
)

SECTION_MAP = {
    "tech": "technology",
    "technology": "technology",
    "ai": "technology",
    "science": "science",
    "space": "science",
    "health": "science",
    "climate": "world",
    "world": "world",
    "business": "world",
    "sports": "world",
    "politics": "world",
}

TAG_RE = re.compile(r"<[^>]+>")


class NewsTool(BaseTool):

    keywords = ("news", "headline", "headlines", "breaking", "latest")

    ttl = 20 * 60

    @property
    def name(self) -> str:
        return "news"

    @property
    def priority(self) -> int:
        return 97

    @property
    def description(self) -> str:
        return "Current headlines from public publisher RSS feeds"

    @property
    def available(self) -> bool:
        return True

    async def execute(self, query: str) -> List[SearchResult]:
        text = (query or "").strip()
        keywords = re.findall(r"[A-Za-z][A-Za-z0-9.+-]{2,}", text)

        stop = {
            "news", "latest", "today", "about", "what", "any", "new", "the",
            "and", "for", "from", "with", "this", "that", "how", "why", "who",
            "is", "are", "was", "were", "in", "on", "at", "of",
        }

        terms = [word for word in keywords if word.lower() not in stop]

        section = SECTION_MAP.get(
            (SECTION_RE.search(text).group(1).lower()
             if SECTION_RE.search(text) else ""),
            "world",
        )

        results: List[SearchResult] = []

        keyed = await self._from_api(text, terms)

        if keyed:
            return keyed

        from utils.settings import settings

        feed_pairs = list(FEEDS.get(section, FEEDS["world"]))

        # Operator supplied feeds (NEWS_FEEDS="Name|url,...") always run, and
        # are searched for every query since they are chosen deliberately.
        for label, url in (settings.news_feeds or {}).items():
            feed_pairs.append((label, url))

        if section != "world":
            for label, url in FEEDS["world"]:
                if url not in [item[1] for item in feed_pairs]:
                    feed_pairs.append((label, url))

        tasks = [
            self._from_feed(label, url, terms)
            for label, url in feed_pairs
        ]

        chunks = await asyncio.gather(*tasks, return_exceptions=True)

        for (label, url), chunk in zip(feed_pairs, chunks):
            if isinstance(chunk, Exception):
                logger.debug("Feed %s failed: %s", label, chunk)
                continue

            results.extend(chunk)

        if terms:
            wanted = {word.lower() for word in terms}

            results = [
                result
                for result in results
                if wanted & set(re.findall(r"[a-z0-9.+-]+", result.content.lower()))
            ] or results

        return results[:8]

    async def _from_feed(self, label: str, url: str, terms) -> List[SearchResult]:
        try:
            xml = await fetch_text(url, timeout=10, retries=0)
        except FetchError as error:
            logger.debug("News feed %s unreachable: %s", label, error)
            return []

        if not self._looks_like_feed(xml):
            # A publisher page that is not actually a feed would otherwise be
            # parsed into nav links and quoted as breaking news.
            logger.warning("News feed %s is not RSS/Atom - skipped", label)

            return []

        try:
            import feedparser

            parsed = feedparser.parse(xml)
            entries = list(parsed.entries or [])

            if not entries and getattr(parsed, "bozo", 0):
                logger.debug("Feed %s parsed empty (bozo): %s", label, parsed.get("exc"))
        except Exception:  # pragma: no cover - fallback parser
            entries = self._fallback_parse(xml)

        scored = []

        for entry in entries[:25]:
            title = getattr(entry, "title", None) or ""
            summary = getattr(entry, "summary", None) or ""
            summary = truncate(html_to_text(summary) or TAG_RE.sub("", summary), 400)
            link = getattr(entry, "link", None)
            published = getattr(entry, "published", None) or getattr(
                entry, "updated", None
            )

            if not title:
                continue

            haystack = f"{title} {summary}".lower()

            score = 1.0
            for term in terms:
                if term.lower() in haystack:
                    score += 1.0

            scored.append(
                (
                    score,
                    SearchResult(
                        title=title.strip(),
                        content=summary or title.strip(),
                        source=label,
                        url=link,
                        published=published,
                        confidence=0.9 if terms else 0.95,
                        category="news",
                        metadata={"feed": url},
                    ).stamp(tool=self.name),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)

        return [item for _, item in scored[:4] if item[0] > 1.0 or not terms]

    @staticmethod
    def _looks_like_feed(payload: str) -> bool:
        head = (payload or "")[:2000].lstrip().lower()

        if not head:
            return False

        if head.startswith("<!doctype html>") or "<html" in head[:400]:
            return False

        return any(
            marker in head
            for marker in ("<rss", "<feed", "<rdf:rss", "<?xml")
        )

    def _fallback_parse(self, xml: str) -> list:
        """Minimal RSS/Atom item extractor for when feedparser is missing."""
        from types import SimpleNamespace

        items = []

        for block in re.findall(r"<(?:item|entry)[\s\S]*?</(?:item|entry)>", xml)[:20]:
            def field(*names, _block=block):
                for name in names:
                    match = re.search(
                        rf"<{name}[^>]*>([\s\S]*?)</{name}>", _block, re.IGNORECASE
                    )
                    if match:
                        value = match.group(1).strip()
                        cdata = re.fullmatch(r"<!\[CDATA\[([\s\S]*?)\]\]>", value)

                        return (cdata.group(1) if cdata else value).strip()
                return ""

            link_match = re.search(
                r"<link[^>]*href=\"([^\"]+)\"", block, re.IGNORECASE
            ) or re.search(r"<link[^>]*>([\s\S]*?)</link>", block, re.IGNORECASE)

            items.append(
                SimpleNamespace(
                    title=field("title"),
                    summary=field("description", "summary"),
                    link=(link_match.group(1).strip() if link_match else ""),
                    published=field("pubDate", "published", "updated", "dc:date"),
                )
            )

        return items

    async def _from_api(self, text: str, terms) -> List[SearchResult]:
        """Use a keyed news API when the operator configured one."""
        api_key = os.getenv("NEWS_API_KEY")
        gnews_key = os.getenv("GNEWS_API_KEY")

        try:
            if api_key:
                data = await fetch_json(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": " ".join(terms) or text,
                        "sortBy": "publishedAt",
                        "pageSize": 6,
                        "apiKey": api_key,
                    },
                    timeout=12,
                )

                articles = (data or {}).get("articles") or []

                return [
                    SearchResult(
                        title=(item.get("title") or "").strip(),
                        content=(item.get("description") or item.get("title") or "").strip(),
                        source=((item.get("source") or {}).get("name")) or "NewsAPI",
                        url=item.get("url"),
                        published=item.get("publishedAt"),
                        confidence=0.93,
                        category="news",
                    ).stamp(tool=self.name)
                    for item in articles
                    if item.get("title")
                ]

            if gnews_key:
                data = await fetch_json(
                    "https://newsapi.gnews.io/query",
                    params={
                        "q": " ".join(terms) or text,
                        "max": 6,
                        "token": gnews_key,
                    },
                    timeout=12,
                )

                return [
                    SearchResult(
                        title=item.get("title", "").strip(),
                        content=item.get("description", "").strip(),
                        source=item.get("source", "GNews"),
                        url=item.get("url"),
                        published=item.get("publishedAt"),
                        confidence=0.9,
                        category="news",
                    ).stamp(tool=self.name)
                    for item in (data or {}).get("articles", [])
                    if item.get("title")
                ]
        except Exception as error:  # noqa: BLE001 - always fall back to feeds
            logger.info("News API failed, using RSS feeds: %s", error)

        return []


news = NewsTool()

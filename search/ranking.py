"""
Project Nexus

Search Ranking

Filters, scores, deduplicates and cross-checks retrieved evidence.

Ranking is the difference between "I found something" and "I found the same
thing in two independent places". A single blog post and three primary
sources both produce results; only the second one deserves to be stated as
fact, so the ranker returns both the ordering and the agreement statistics
that the verifier uses.
"""

import re
from typing import List

from search.freshness import MEDIUM, confidence_from_age
from search.query import domain_of, similarity
from search.search_result import SearchResult
from utils.logger import logger

#: Source-level trust. A domain beats a tool name because a web search
#: returns the domain, not the search engine.
DOMAIN_AUTHORITY = {
    "wikipedia.org": 0.98,
    "wikimedia.org": 0.96,
    "arxiv.org": 0.99,
    "github.com": 0.96,
    "gitlab.com": 0.9,
    "stackoverflow.com": 0.95,
    "stackexchange.com": 0.92,
    "nature.com": 0.98,
    "science.org": 0.97,
    "pubmed.ncbi.nlm.nih.gov": 0.98,
    "nih.gov": 0.97,
    "who.int": 0.97,
    "un.org": 0.96,
    "worldbank.org": 0.96,
    "imf.org": 0.96,
    "oecd.org": 0.95,
    "nasa.gov": 0.98,
    "iso.org": 0.95,
    "iucr.org": 0.95,
    "open-meteo.com": 0.99,
    "exchangerate-api.com": 0.97,
    "frankfurter.app": 0.97,
    "ec.europa.eu": 0.95,
    "europa.eu": 0.94,
    "go.gov": 0.97,
    "gov.in": 0.96,
    "gov.uk": 0.96,
    ".gov": 0.97,
    ".edu": 0.94,
    ".ac.uk": 0.94,
    "ac.in": 0.93,
    "reuters.com": 0.96,
    "apnews.com": 0.96,
    "bbc.co.uk": 0.95,
    "bbc.com": 0.95,
    "theguardian.com": 0.93,
    "nytimes.com": 0.93,
    "washingtonpost.com": 0.92,
    "bloomberg.com": 0.95,
    "ft.com": 0.95,
    "aljazeera.com": 0.9,
    "npr.org": 0.92,
    "associatedpress.com": 0.95,
    "theverge.com": 0.88,
    "arstechnica.com": 0.9,
    "techcrunch.com": 0.86,
    "hnrss.org": 0.7,
    "news.ycombinator.com": 0.7,
    "reddit.com": 0.62,
    "quora.com": 0.45,
    "medium.com": 0.45,
    "pinterest.com": 0.25,
    "facebook.com": 0.3,
    "x.com": 0.4,
    "twitter.com": 0.4,
    "instagram.com": 0.3,
    "youtube.com": 0.6,
    "tradingview.com": 0.75,
    "coingecko.com": 0.8,
    "coinmarketcap.com": 0.82,
    "imdb.com": 0.85,
    "rottentomatoes.com": 0.8,
    "steampowered.com": 0.95,
    "openstreetmap.org": 0.9,
    "spotify.com": 0.9,
    "duckduckgo.com": 0.8,
    "mymemory.translated.net": 0.85,
}

#: Tool-reported sources without a URL still get a sane prior.
SOURCE_AUTHORITY = {
    "Open-Meteo": 1.0,
    "IANA Time Zone Database": 1.0,
    "Calculator": 1.0,
    "ExchangeRate-API": 0.99,
    "Frankfurter (ECB)": 0.99,
    "Wikipedia": 0.96,
    "GitHub": 0.97,
    "Stack Overflow": 0.95,
    "arXiv": 0.98,
    "Brave Search": 0.9,
    "Google": 0.9,
    "OpenRouter Search": 0.88,
    "Gemini Search": 0.88,
    "News": 0.9,
    "Steam": 0.97,
    "Spotify": 0.96,
    "OpenStreetMap": 0.94,
    "MyMemory": 0.8,
    "LibreTranslate": 0.8,
    "Reddit": 0.6,
    "DuckDuckGo": 0.78,
    "File Reader": 1.0,
    "Web Scraper": 0.7,
}

DISCOUNT_SOURCES = {
    "YouTube": 0.8,
    "Reddit": 0.65,
    "DuckDuckGo": 0.9,
}

# Content that is never evidence, whatever the confidence field claims.
PLACEHOLDER_PATTERNS = (
    "under development",
    "not implemented",
    "integration is not",
    "coming soon",
    "todo:",
    "placeholder",
    "no results",
    "api key",
)

MONEY_RE = re.compile(r"[$€£₹]\s?\d[\d,]*(?:\.\d+)?\s*(?:billion|million|trillion|bn|m|k)?", re.IGNORECASE)
PERCENT_RE = re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%")
TEMP_RE = re.compile(r"-?\d{1,3}(?:\.\d+)?\s?°[FC]\b")
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
HEADLINE_SOURCES = ("news", "headline")


class SearchRanking:

    # ==========================================
    # Public API
    # ==========================================

    def rank(
        self,
        results: List[SearchResult],
        query: str | None = None,
        *,
        budget: int | None = None,
        max_results: int | None = None,
    ) -> List[SearchResult]:
        """
        Filter junk, score what is left and order it best-first.

        Only usable results survive: a failure, a placeholder string, an empty
        body or a page with no text never reaches the model.
        """
        logger.info(
            f"Ranking {len(results or [])} results."
        )

        if not results:
            return []

        budget = budget if budget is not None else MEDIUM

        scored: List[SearchResult] = []
        seen_domains: dict[str, int] = {}
        seen: list[tuple[str, SearchResult]] = []

        for result in results:
            if not self.is_usable(result):
                continue

            if not result.domain:
                result.domain = domain_of(result.url) or (result.source or "").lower()

            result.confidence = self._clamp(result.confidence)

            authority = self.authority(result)

            freshness = confidence_from_age(result.age, budget)

            relevance = self._relevance(result, query) if query else 1.0

            multiplicity = 1.0 + min(
                seen_domains.get(result.domain or "", 0) * 0.04, 0.12
            )

            result.score = self._clamp(
                result.confidence
                * authority
                * freshness
                * relevance
                * multiplicity
                * DISCOUNT_SOURCES.get(result.source, 1.0)
            )

            result.tags.append(
                f"age:{'unknown' if result.age is None else int(result.age)}s"
            )

            signature = self._signature(result)

            duplicate = self._find_duplicate(signature, seen)

            if duplicate is not None:
                # Same article reached us through two tools: keep the stronger
                # copy so ranking is not inflated by one recycled page.
                duplicate.tags.append("recycled")

                if result.score_of() > duplicate.score_of():
                    scored.remove(duplicate)
                    seen = [item for item in seen if item[1] is not duplicate]
                    seen.append((signature, result))
                    scored.append(result)
                else:
                    duplicate.metadata.setdefault("also_from", []).append(
                        result.source
                    )

                result.tags.append("duplicate")
                continue

            seen.append((signature, result))
            scored.append(result)

            if result.domain:
                seen_domains[result.domain] = seen_domains.get(result.domain, 0) + 1

        scored.sort(key=lambda item: item.score_of(), reverse=True)

        if max_results:
            scored = scored[:max_results]

        logger.info(
            f"{len(scored)} ranked results."
        )

        return scored

    def cross_check(self, results: List[SearchResult]) -> dict:
        """
        How much do these sources actually agree?

        Returns the numbers the verifier reasons over: independent domains,
        corroborated top claim, and value conflicts (a price quoted two ways,
        two different years, ...) that must be surfaced instead of averaged.
        """
        if not results:
            return {
                "sources": 0,
                "domains": [],
                "corroborated": False,
                "confidence": 0.0,
                "conflicts": [],
                "notes": [],
            }

        # One story copied onto two sites is one story: count a domain only
        # once per distinct text, so syndication cannot fake corroboration.
        seen_signatures: dict[str, str] = {}

        for result in results:
            domain = result.domain or domain_of(result.url)

            if not domain:
                continue

            signature = self._signature(result)

            previous = seen_signatures.get(signature)

            if previous and previous != domain:
                # Same words, different site: the first domain already counted.
                continue

            seen_signatures.setdefault(signature, domain)

        domains = list(dict.fromkeys(seen_signatures.values()))

        unique_domains = domains or ["(unknown)"]

        top = results[0]

        corroborated = len(unique_domains) >= 2 and top.score_of() >= 0.6

        conflicts = self._conflicts(results[:5])

        notes = []

        if len(unique_domains) == 1 and len(results) > 1:
            notes.append(
                f"all {len(results)} results came from a single source "
                f"({unique_domains[0]})"
            )

        if top.published_at is None and top.published is None:
            notes.append("the best source has no publication date")

        for conflict in conflicts:
            notes.append(
                f"sources disagree about {conflict['kind']}: "
                + " vs ".join(conflict["values"][:3])
            )

        mean_confidence = sum(
            result.score_of() for result in results
        ) / len(results)

        return {
            "sources": len(unique_domains),
            "domains": unique_domains,
            "corroborated": corroborated,
            "confidence": round(mean_confidence, 3),
            "top_confidence": round(top.score_of(), 3),
            "conflicts": conflicts,
            "notes": notes,
            "freshness": (
                "unknown" if top.age is None else self._age_label(top.age)
            ),
        }

    def is_usable(self, result: SearchResult) -> bool:
        """Reject anything that cannot support a factual answer."""
        if result is None:
            return False

        if isinstance(result, dict):
            return False

        if not getattr(result, "success", False):
            return False

        content = (getattr(result, "content", "") or "").strip()
        title = (getattr(result, "title", "") or "").strip()

        if len(content) < 25 or not title:
            return False

        lowered = content.lower()

        if any(pattern in lowered for pattern in PLACEHOLDER_PATTERNS):
            logger.info(
                "Dropped placeholder result from %s: %r",
                result.source,
                title[:60],
            )
            return False

        if lowered in {t.lower() for t in ("error", "failed", "n/a", "none")}:
            return False

        # A page that scraped to its own cookie banner is not evidence.
        if "enable javascript" in lowered and len(content) < 200:
            return False

        return True

    # ==========================================
    # Scoring helpers
    # ==========================================

    def authority(self, result: SearchResult) -> float:
        domain = result.domain or domain_of(result.url)

        if domain:
            for known, weight in DOMAIN_AUTHORITY.items():
                if domain == known or domain.endswith("." + known) or (
                    known.startswith(".") and domain.endswith(known)
                ):
                    return weight

            # Any other .gov / .edu style domain still outranks a random blog.
            if domain.endswith((".gov", ".gov.in", ".gov.uk", ".ac.uk", ".edu")):
                return 0.95

        return SOURCE_AUTHORITY.get(result.source, 0.8)

    def _relevance(self, result: SearchResult, query: str) -> float:
        """Overlap between the question and the evidence, 0.55 - 1.15."""
        from search.query import tokens

        wanted = {word for word in tokens(query) if len(word) > 2}

        if not wanted:
            return 1.0

        haystack = " ".join(
            [result.title or "", (result.content or "")[:900]]
        ).lower()

        hits = sum(1 for word in wanted if word in haystack)

        ratio = hits / len(wanted)

        return 0.55 + 0.6 * ratio

    def _conflicts(self, results: List[SearchResult]) -> list[dict]:
        found = []

        for kind, pattern in (
            ("price", MONEY_RE),
            ("percentage", PERCENT_RE),
            ("temperature", TEMP_RE),
        ):
            values = []

            for result in results:
                for match in pattern.findall(result.content or ""):
                    text = match if isinstance(match, str) else match[0]

                    text = re.sub(r"\s+", " ", text).strip()

                    if text and text not in values:
                        values.append(text)

            # Two different figures = a real disagreement; three different
            # temperatures across a 3-day forecast is just a forecast.
            if kind != "temperature" and len(values) >= 2:
                found.append({"kind": kind, "values": values[:4]})

        return found

    def _signature(self, result: SearchResult) -> str:
        return re.sub(
            r"\s+", " ", (result.content or "")[:600]
        ).strip().lower()

    def _find_duplicate(
        self,
        signature: str,
        seen: list[tuple[str, SearchResult]],
    ) -> SearchResult | None:
        """Return an already-ranked result carrying the same text."""
        for previous, result in seen:
            if signature == previous or similarity(signature, previous) > 0.93:
                return result

        return None

    def _age_label(self, age: float) -> str:
        from utils.time_utils import DAY, HOUR, WEEK

        if age < HOUR:
            return "minutes old"
        if age < DAY:
            return "hours old"
        if age < WEEK * 4:
            return "days old"
        if age < WEEK * 26:
            return "weeks old"

        return "months or more old"

    def _clamp(self, value: float) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.5

        return max(0.0, min(1.0, value))

    # ==========================================
    # Compatibility
    # ==========================================

    def best(
        self,
        results: List[SearchResult],
    ) -> SearchResult | None:
        ranked = self.rank(results)

        if not ranked:

            return None

        return ranked[0]


ranking = SearchRanking()

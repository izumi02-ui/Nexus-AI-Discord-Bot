"""
Project Nexus

Search Result

Standard object shared between every search provider.

Beyond the headline fields, results carry provenance (where they came from,
when they were fetched, when they were published) so the ranking layer can
discount stale or single-sourced information and the answer verifier can
refuse to print a URL that no tool actually returned.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from search.query import domain_of
from utils.time_utils import age_seconds, now_utc, parse_datetime


@dataclass
class SearchResult:

    # ==========================================
    # Core
    # ==========================================

    title: str

    content: str

    source: str

    confidence: float = 1.0

    # ==========================================
    # URLs
    # ==========================================

    url: Optional[str] = None

    image: Optional[str] = None

    thumbnail: Optional[str] = None

    video: Optional[str] = None

    # ==========================================
    # Metadata
    # ==========================================

    author: Optional[str] = None

    published: Optional[str] = None

    language: Optional[str] = None

    category: Optional[str] = None

    # ==========================================
    # Status
    # ==========================================

    success: bool = True

    error: Optional[str] = None

    # ==========================================
    # Provenance (filled in by the aggregator)
    # ==========================================

    tool: Optional[str] = None

    domain: Optional[str] = None

    fetched_at: Optional[str] = None

    published_at: Optional[str] = None

    # Final ranking score, distinct from the raw source confidence.
    score: float = 0.0

    # ==========================================
    # Extra
    # ==========================================

    tags: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    raw: Any = None

    # ==========================================
    # Helper
    # ==========================================

    def is_valid(self) -> bool:

        return (

            self.success

            and bool(self.content)

            and bool(self.title)

        )

    def score_of(self) -> float:
        """Final ranking score, falling back to raw source confidence."""
        return self.score or self.confidence

    # ==========================================
    # Provenance helpers
    # ==========================================

    def stamp(self, tool: str | None = None) -> "SearchResult":
        """Attach fetch time, tool name and domain to a result."""
        if tool:
            self.tool = tool

        if not self.fetched_at:
            self.fetched_at = now_utc().isoformat(timespec="seconds")

        if not self.domain:
            self.domain = domain_of(self.url) or (self.source or "").lower()

        if not self.published_at and self.published:
            parsed = parse_datetime(self.published)

            if parsed:
                self.published_at = parsed.isoformat(timespec="seconds")

        return self

    @property
    def age(self) -> float | None:
        """
        Age of the underlying information.

        Prefer the publication date (that is when the claim was made); fall
        back to the fetch date, which is the most recent we can vouch for.
        """
        for value in (self.published_at, self.published, self.fetched_at):
            seconds = age_seconds(value)

            if seconds is not None:
                return seconds

        return None

    def is_stale(self, budget_seconds: int) -> bool:
        """True when the result is older than the query's freshness budget."""
        if budget_seconds <= 0:
            return False

        age = self.age

        if age is None:
            # Unknown age is not proof of freshness.
            return bool(self.published) is False and self.confidence < 1.0

        return age > budget_seconds

    def citation(self) -> str:
        """Compact attribution used in the evidence block and in /sources."""
        parts = [self.source or self.tool or "unknown"]

        if self.published_at:
            parts.append(f"published {self.published_at[:10]}")
        elif self.fetched_at:
            parts.append(f"fetched {self.fetched_at[:10]}")

        text = " · ".join(parts)

        if self.url:
            text += f" · {self.url}"

        return text

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "url": self.url,
            "confidence": round(self.confidence, 3),
            "score": round(self.score_of(), 3),
            "published": self.published_at or self.published,
            "fetched": self.fetched_at,
            "tool": self.tool,
        }

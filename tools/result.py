"""
Project Nexus

Tool Result

Uniform return type for tools that answer with a single blob instead of a
list of SearchResult objects (provider-backed tools such as web search).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:

    success: bool = True

    content: str = ""

    error: str | None = None

    source: str = "Tool"

    url: str | None = None

    confidence: float = 1.0

    metadata: dict[str, Any] = field(default_factory=dict)

    raw: Any = None

    @classmethod
    def ok(cls, content, **kwargs) -> "ToolResult":
        return cls(success=True, content=str(content), **kwargs)

    @classmethod
    def fail(cls, error, **kwargs) -> "ToolResult":
        return cls(success=False, error=str(error), **kwargs)

    def to_search_result(self):
        """Adapt into the shared SearchResult used by the search pipeline."""
        from search.search_result import SearchResult

        return SearchResult(
            title=self.metadata.get("title") or self.source,
            content=self.content,
            source=self.source,
            url=self.url,
            confidence=self.confidence,
            metadata=self.metadata,
            raw=self.raw,
        )

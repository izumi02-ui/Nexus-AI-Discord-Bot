"""
Project Nexus

Search Result

Standard object shared between
every search provider.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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

    def score(self) -> float:

        return self.confidence

"""
Project Nexus

Search Result

Standard object returned by
every search tool.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:

    title: str

    content: str

    source: str

    url: Optional[str] = None

    image: Optional[str] = None

    confidence: float = 1.0

    success: bool = True

    error: Optional[str] = None

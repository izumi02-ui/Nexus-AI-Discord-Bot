"""
Project Nexus

Tool Call
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:

    tool: str

    query: str

    arguments: dict[str, Any] | None = None

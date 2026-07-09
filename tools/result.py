"""
Project Nexus

Tool Result
"""

from dataclasses import dataclass


@dataclass
class ToolResult:

    success: bool

    content: str | None = None

    error: str | None = None

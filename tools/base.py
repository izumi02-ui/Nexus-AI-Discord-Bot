"""
Project Nexus

Base Tool

Every tool must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List

from search.search_result import SearchResult


class BaseTool(ABC):
    """
    Base class for every Nexus tool.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name.
        """
        pass

    @property
    def enabled(self) -> bool:
        """
        Whether the tool is enabled.
        """

        return True

    @property
    def priority(self) -> int:
        """
        Higher priority tools are executed first.
        """

        return 100

    @property
    def description(self) -> str:
        """
        Human-readable tool description.
        """

        return self.name

    @abstractmethod
    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:
        """
        Execute the tool.

        Returns:
            List[SearchResult]
        """
        raise NotImplementedError

    async def healthcheck(self) -> bool:
        """
        Used by ToolManager.
        """

        return True

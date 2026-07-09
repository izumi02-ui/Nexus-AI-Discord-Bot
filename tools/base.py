"""
Project Nexus

Base Tool
"""

from abc import ABC, abstractmethod

from tools.result import ToolResult


class BaseTool(ABC):

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    async def execute(
        self,
        query: str,
    ) -> ToolResult:
        pass

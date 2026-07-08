"""
Project Nexus

Base Tool

Every Nexus tool must inherit from this class.
"""

from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    Base class for every tool.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name.
        """
        pass

    @abstractmethod
    async def execute(
        self,
        query: str,
    ):
        """
        Execute the tool.
        """
        pass

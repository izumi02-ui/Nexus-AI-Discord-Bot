"""
Project Nexus

Base AI Provider
"""

from abc import ABC, abstractmethod
from typing import List, Dict

from ai.provider_capabilities import ProviderCapabilities


class BaseProvider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        pass

    @abstractmethod
    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:
        pass

    @abstractmethod
    async def use_tool(
        self,
        tool: str,
        query: str,
    ):
        """
        Execute a provider tool.

        Example:
            web_search
            vision
            image_generation
        """
        pass

    def supports(
        self,
        capability: str,
    ) -> bool:

        return self.capabilities.supports(
            capability
        )

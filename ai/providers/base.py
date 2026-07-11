"""
Project Nexus

Base AI Provider
"""

from abc import ABC, abstractmethod
from typing import Dict, List

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

    @property
    @abstractmethod
    def model(self) -> str:
        pass

    @property
    def available(self) -> bool:
        return True

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
        pass

    def supports(
        self,
        capability: str,
    ) -> bool:

        return self.capabilities.supports(
            capability
        )

    def info(self) -> dict:

        return {

            "name": self.name,

            "model": self.model,

            "available": self.available,

            "capabilities": self.capabilities.__dict__,

        }

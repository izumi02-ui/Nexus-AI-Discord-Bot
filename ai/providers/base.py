"""
Project Nexus

Base AI Provider

Every AI provider must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict

from ai.provider_capabilities import ProviderCapabilities


class BaseProvider(ABC):
    """
    Base class for all AI providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable provider name.
        """
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """
        Provider capabilities.
        """
        pass

    @abstractmethod
    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:
        """
        Send a conversation to an AI provider.

        Args:
            user_id:
                Discord user ID.

            conversation:
                List of conversation messages.

        Returns:
            AI response.
        """
        raise NotImplementedError

    def supports(
        self,
        capability: str,
    ) -> bool:
        """
        Check whether the provider supports
        a capability.
        """

        return self.capabilities.supports(
            capability
        )
"""
Project Nexus

Base AI Provider

Every AI provider must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict


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

"""
Project Nexus

Base AI Provider

Every AI provider must inherit from this class.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """
    Base class for every AI provider.
    """

    @abstractmethod
    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:
        """
        Send a conversation to the AI provider.

        Parameters:
            user_id: Discord User ID
            conversation: Complete conversation history

        Returns:
            AI response as a string.
        """
        pass

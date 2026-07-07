"""
Project Nexus

AI Engine

The AI Engine is the heart of Nexus.
Every AI request passes through here.

Discord never talks directly to Gemini,
Groq, OpenRouter, or any future provider.

Instead, Discord asks the Engine,
and the Engine decides which provider to use.
"""

from ai.provider import ProviderManager


class AIEngine:
    """
    Main AI Engine
    """

    def __init__(self):

        self.provider = ProviderManager()

    async def ask(
        self,
        user_id: int,
        message: str,
    ) -> str:
        """
        Send a message to the active AI provider.
        """

        return await self.provider.ask(
            user_id=user_id,
            message=message
        )


# Global Engine
engine = AIEngine()

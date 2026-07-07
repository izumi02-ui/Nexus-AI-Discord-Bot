"""
Project Nexus

Provider Manager
"""

from ai.providers.gemini import GeminiProvider
from utils.logger import logger


class ProviderManager:

    def __init__(self):

        logger.info("Loading Gemini Provider...")

        self.provider = GeminiProvider()

        logger.info("Gemini Provider Loaded.")

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        return await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

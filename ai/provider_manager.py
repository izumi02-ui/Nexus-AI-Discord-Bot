"""
Project Nexus

Provider Manager
"""

from utils.logger import logger
from ai.providers.gemini import GeminiProvider


class ProviderManager:

    def __init__(self):

        logger.info("Loading Provider...")

        self.provider = GeminiProvider()

        logger.info("Provider Loaded.")

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        return await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )


provider_manager = ProviderManager()

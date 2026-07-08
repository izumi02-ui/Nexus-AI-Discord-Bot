"""
Project Nexus

Provider Manager

Responsible for selecting and managing
the active AI provider.
"""

from ai.providers.gemini import GeminiProvider

from utils.logger import logger
from utils.settings import settings


class ProviderManager:

    def __init__(self):

        self.provider = self._load_provider()

    def _load_provider(self):

        provider = settings.provider.lower()

        logger.info(f"Loading provider: {provider}")

        if provider == "gemini":

            return GeminiProvider()

        raise ValueError(
            f"Unknown provider: {provider}"
        )

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        return await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

    @property
    def name(self):

        return self.provider.name


provider_manager = ProviderManager()

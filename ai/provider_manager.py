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

        self.providers = {

            "gemini": GeminiProvider(),

            # Future Providers
            # "groq": GroqProvider(),
            # "openrouter": OpenRouterProvider(),
            # "gpt": OpenAIProvider(),
            # "claude": ClaudeProvider(),
            # "deepseek": DeepSeekProvider(),

        }

        self.provider = self._load_provider()

    # ==========================================
    # Load Provider
    # ==========================================

    def _load_provider(self):

        provider_name = settings.provider.lower()

        logger.info(
            f"Loading provider: {provider_name}"
        )

        provider = self.providers.get(
            provider_name
        )

        if provider is None:

            raise ValueError(
                f"Unknown provider: {provider_name}"
            )

        return provider

    # ==========================================
    # Change Provider
    # ==========================================

    def set_provider(
        self,
        provider_name: str,
    ):

        provider_name = provider_name.lower()

        provider = self.providers.get(
            provider_name
        )

        if provider is None:

            raise ValueError(
                f"Unknown provider: {provider_name}"
            )

        self.provider = provider

        settings.provider = provider_name

        logger.info(
            f"Provider changed to {provider_name}"
        )

    # ==========================================
    # Ask
    # ==========================================

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        return await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

    # ==========================================
    # Information
    # ==========================================

    @property
    def name(self):

        return self.provider.name

    @property
    def available(self):

        return list(
            self.providers.keys()
        )


provider_manager = ProviderManager()

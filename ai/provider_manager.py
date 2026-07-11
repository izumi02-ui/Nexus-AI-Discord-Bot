"""
Project Nexus

Provider Manager
"""

from ai.providers.gemini import GeminiProvider
from ai.providers.openai import OpenAIProvider
from ai.providers.openrouter import OpenRouterProvider
from ai.providers.groq import GroqProvider
from ai.providers.claude import ClaudeProvider
from ai.providers.deepseek import DeepSeekProvider
# from ai.providers.mistral import MistralProvider
from ai.providers.cohere import CohereProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.lmstudio import LMStudioProvider

from utils.logger import logger
from utils.settings import settings


class ProviderManager:

    def __init__(self):

        self.providers = {}

        self._register()

        self.provider = self._load_provider()

    # =====================================
    # Register Providers
    # =====================================

    def _register(self):

        self._add("gemini", GeminiProvider)
        self._add("openai", OpenAIProvider)
        self._add("openrouter", OpenRouterProvider)
        self._add("groq", GroqProvider)
        self._add("claude", ClaudeProvider)
        self._add("deepseek", DeepSeekProvider)
        # self._add("mistral", MistralProvider)
        self._add("cohere", CohereProvider)
        self._add("ollama", OllamaProvider)
        self._add("lmstudio", LMStudioProvider)

    # =====================================
    # Add Provider
    # =====================================

    def _add(
        self,
        name: str,
        cls,
    ):

        try:

            provider = cls()

            self.providers[name] = provider

            logger.info(
                f"{name} loaded."
            )

        except Exception as error:

            logger.warning(
                f"{name} unavailable: {error}"
            )

    # =====================================
    # Load Default Provider
    # =====================================

    def _load_provider(self):

        provider = self.providers.get(
            settings.provider.lower()
        )

        if provider:

            return provider

        if not self.providers:

            raise RuntimeError(
                "No AI providers available."
            )

        provider = next(
            iter(self.providers.values())
        )

        logger.warning(
            f"Default provider unavailable. Using {provider.name}."
        )

        return provider

    # =====================================
    # Ask
    # =====================================

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        providers = list(
            self.providers.values()
        )

        start = providers.index(
            self.provider
        )

        ordered = (

            providers[start:]

            +

            providers[:start]

        )

        last_error = None

        for provider in ordered:

            try:

                logger.info(
                    f"Trying {provider.name}"
                )

                self.provider = provider

                return await provider.ask(

                    user_id=user_id,

                    conversation=conversation,

                )

            except Exception as error:

                last_error = error

                logger.exception(
                    f"{provider.name} failed."
                )

        raise RuntimeError(
            f"All providers failed.\n{last_error}"
        )

    # =====================================
    # Change Provider
    # =====================================

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

    # =====================================
    # Capability Check
    # =====================================

    def supports(
        self,
        capability: str,
    ) -> bool:

        return self.provider.supports(
            capability
        )

    # =====================================
    # Properties
    # =====================================

    @property
    def available(self):

        return sorted(
            self.providers.keys()
        )

    @property
    def name(self):

        return self.provider.name

    @property
    def model(self):

        return self.provider.model

    @property
    def info(self):

        return self.provider.info()


provider_manager = ProviderManager()

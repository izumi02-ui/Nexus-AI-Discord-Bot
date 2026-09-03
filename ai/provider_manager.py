"""
Project Nexus

Provider Manager

Chooses which AI provider answers, and keeps a bad night from becoming a
permanent outage.

Fallback rules that matter:

  * a provider that fails repeatedly is put in a short cooldown instead of
    being retried on every single message;
  * the configured default stays the default - the old code reassigned it to
    whichever provider happened to answer first, so one 429 from the free
    tier moved the bot onto a weaker model for the rest of the day;
  * every answer records which provider and model produced it, which is what
    /status shows and what the self-updater uses to repair the model chain.
"""

import time

from ai.providers.gemini import GeminiProvider
from ai.providers.openai import OpenAIProvider
from ai.providers.openrouter import OpenRouterProvider
from ai.providers.groq import GroqProvider
from ai.providers.claude import ClaudeProvider
from ai.providers.deepseek import DeepSeekProvider
from ai.providers.mistral import MistralProvider
from ai.providers.cohere import CohereProvider
from ai.providers.ollama import OllamaProvider
from ai.providers.lmstudio import LMStudioProvider

from utils.logger import logger
from utils.settings import settings

#: Providers whose quality is high enough to be worth retrying. Ordered list of
#: fallbacks used when a capability (vision, grounding) is required.
QUALITY_ORDER = [
    "openrouter",
    "openai",
    "gemini",
    "claude",
    "deepseek",
    "groq",
    "cohere",
    "mistral",
    "ollama",
    "lmstudio",
]


class ProviderBreaker:
    """Tiny circuit breaker so a rate-limited provider stops eating requests."""

    FAILURE_LIMIT = 2
    COOLDOWN = 120

    def __init__(self):
        self.failures = 0
        self.open_until = 0.0
        self.last_error = None
        self.successes = 0
        self.last_latency = None
        self.total_seconds = 0.0
        self.requests = 0

    @property
    def open(self) -> bool:
        return self.open_until > time.time()

    def record_success(self, latency: float):
        self.failures = 0
        self.successes += 1
        self.requests += 1
        self.open_until = 0.0
        self.last_latency = round(latency, 2)
        self.total_seconds += latency

    def record_failure(self, error):
        self.requests += 1
        self.failures += 1
        self.last_error = str(error)[:300]

        if self.failures >= self.FAILURE_LIMIT:
            self.open_until = time.time() + self.COOLDOWN

            logger.warning(
                "Provider breaker opened for %s more failures; cooling down %ss.",
                self.failures,
                self.COOLDOWN,
            )

    def stats(self) -> dict:
        return {
            "requests": self.requests,
            "successes": self.successes,
            "failures": self.failures,
            "cooling_down": self.open,
            "avg_latency": (
                round(self.total_seconds / self.successes, 2) if self.successes else None
            ),
            "last_error": self.last_error,
        }


class ProviderManager:

    def __init__(self):

        self.providers = {}

        self.breakers = {}

        self.last = None

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
        self._add("cohere", CohereProvider)
        self._add("mistral", MistralProvider)
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

            self.breakers[name] = ProviderBreaker()

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

        preferred = (settings.provider or "").lower()

        provider = self.providers.get(preferred)

        if provider:

            return provider

        if not self.providers:

            raise RuntimeError(
                "No AI providers available."
            )

        # Pick the best available provider rather than an arbitrary one.
        for name in QUALITY_ORDER:
            if name in self.providers:
                logger.warning(
                    "Default provider %r is not available. Using %s.",
                    preferred,
                    name,
                )

                return self.providers[name]

        provider = next(iter(self.providers.values()))

        logger.warning(
            "Default provider unavailable. Using %s.",
            provider.name,
        )

        return provider

    # =====================================
    # Order to try for one request
    # =====================================

    def _candidates(self, *, capability: str | None = None) -> list:
        """
        Preferred provider first, then the others, respecting the breakers.

        Local providers (Ollama / LM Studio) rank last: answering from a 4B
        model is worse than answering a second later from a much bigger one, so
        they are a safety net rather than the default path.
        """

        def rank(provider) -> int:
            key = provider_key(provider)

            return QUALITY_ORDER.index(key) if key in QUALITY_ORDER else len(QUALITY_ORDER)

        ordered = sorted(self.providers.values(), key=rank)

        # The configured default always gets the first attempt.
        if self.provider in ordered:
            ordered.remove(self.provider)
            ordered.insert(0, self.provider)

        if capability:
            capable = [provider for provider in ordered if provider.supports(capability)]
            others = [provider for provider in ordered if provider not in capable]

            ordered = capable + others

        healthy = []

        for provider in ordered:
            breaker = self.breakers.setdefault(provider_key(provider), ProviderBreaker())

            if provider.available and not breaker.open:
                healthy.append(provider)

        # Everything is cooling down: try the highest quality option anyway so
        # the bot keeps answering instead of refusing forever.
        return healthy or ordered

    # =====================================
    # Ask
    # =====================================

    async def ask(
        self,
        user_id: int,
        conversation: list,
        *,
        capability: str | None = None,
    ) -> str:
        result = await self.ask_with_info(
            user_id=user_id,
            conversation=conversation,
            capability=capability,
        )

        return result["response"]

    async def ask_with_info(
        self,
        user_id: int,
        conversation: list,
        *,
        capability: str | None = None,
    ) -> dict:
        """
        Answer, falling back across providers.

        Returns the text together with the provider/model that produced it so
        the engine, the API and /status can all show where an answer came
        from.
        """
        if not self.providers:
            raise RuntimeError("No AI providers are configured.")

        last_error = None

        for provider in self._candidates(capability=capability):
            key = provider_key(provider)

            breaker = self.breakers.setdefault(key, ProviderBreaker())

            started = time.monotonic()

            try:
                logger.info(
                    "Trying %s (%s)",
                    provider.name,
                    provider.model,
                )

                response = await provider.ask(
                    user_id=user_id,
                    conversation=conversation,
                )

                if not response or not str(response).strip():
                    raise RuntimeError(
                        f"{provider.name} returned an empty response."
                    )

                breaker.record_success(time.monotonic() - started)

                self.last = {
                    "provider": key,
                    "model": provider.model,
                    "seconds": round(time.monotonic() - started, 2),
                }

                return {
                    "response": str(response).strip(),
                    "provider": provider.name,
                    "provider_key": key,
                    "model": provider.model,
                    "seconds": round(time.monotonic() - started, 2),
                }

            except Exception as error:
                last_error = error

                breaker.record_failure(error)

                logger.warning(
                    "%s failed: %s",
                    provider.name,
                    str(error)[:200],
                )

        raise RuntimeError(
            "All providers failed. "
            f"Last error: {last_error}"
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
                f"Unknown provider: {provider_name}. "
                f"Loaded: {', '.join(self.available)}"
            )

        self.provider = provider

        settings.provider = provider_name

        logger.info(
            f"Provider changed to {provider_name}"
        )

        return provider

    def reset_breakers(self, provider_name: str | None = None):
        keys = [provider_name] if provider_name else list(self.breakers)

        for key in keys:
            breaker = self.breakers.get(key)

            if breaker:
                breaker.open_until = 0.0
                breaker.failures = 0

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

    def provider_supporting(self, capability: str):
        """Any available provider with a capability, or None."""
        for provider in self._candidates(capability=capability):
            if provider.supports(capability):
                return provider

        return None

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

    def status(self) -> dict:
        return {
            "active": provider_key(self.provider),
            "model": self.provider.model,
            "available": self.available,
            "last_answer": self.last,
            "breakers": {
                key: breaker.stats()
                for key, breaker in sorted(self.breakers.items())
            },
            "providers": {
                key: {
                    "model": provider.model,
                    "available": provider.available,
                    "capabilities": provider.capabilities.to_dict(),
                }
                for key, provider in sorted(self.providers.items())
            },
        }


def provider_key(provider) -> str:
    """Map a provider instance to its registry key."""
    name = (getattr(provider, "name", "") or "").lower().replace(" ", "")

    aliases = {
        "openai": "openai",
        "openrouter": "openrouter",
        "gemini": "gemini",
        "claude": "claude",
        "anthropic": "claude",
        "groq": "groq",
        "deepseek": "deepseek",
        "cohere": "cohere",
        "ollama": "ollama",
        "lmstudio": "lmstudio",
    }

    return aliases.get(name, name)


provider_manager = ProviderManager()

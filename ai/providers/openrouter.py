"""
Project Nexus

OpenRouter Provider with automatic model fallbacks.
"""

from typing import Dict, List

from openai import AsyncOpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class OpenRouterProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "OpenRouter"

    @property
    def model(self) -> str:
        return self.models[0]

    @property
    def capabilities(self):
        return ProviderCapabilities(
            vision=True,
            files=True,
            function_calling=True,
            reasoning=True,
            streaming=True,
            # OpenRouter's "web" plugin grounds any model in live search.
            web_search=bool(getattr(settings, "openrouter_web_search", False)),
        )

    @property
    def available(self) -> bool:
        return bool(settings.openrouter_api_key)

    def __init__(self):
        if not self.available:
            raise RuntimeError(
                "OPENROUTER_API_KEY is missing."
            )

        self.models = [
            model.strip()
            for model in settings.openrouter_models
            if model.strip()
        ]

        if not self.models:
            raise RuntimeError(
                "No OpenRouter models are configured."
            )

        logger.info(
            "Initializing OpenRouter with model chain: %s",
            " -> ".join(self.models),
        )

        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            max_retries=1,
        )

        logger.info("OpenRouter ready.")

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
        *,
        grounded: bool | None = None,
    ) -> str:
        primary_model = self.models[0]
        fallback_models = self.models[1:]

        extra_body = {}

        if fallback_models:
            extra_body["models"] = fallback_models

        if grounded is None:
            grounded = bool(getattr(settings, "openrouter_web_search", False))

        if grounded:
            # Server-side web grounding: OpenRouter runs the search and injects
            # the results, which works even on free models that have no browse
            # ability of their own.
            extra_body["plugins"] = [
                {
                    "id": "web",
                    "max_results": int(getattr(settings, "openrouter_search_results", 5)),
                }
            ]

        request_options = {
            "model": primary_model,
            "messages": conversation,
        }

        if extra_body:
            request_options["extra_body"] = extra_body

        logger.info(
            "OpenRouter request for user %s. Chain: %s",
            user_id,
            " -> ".join(self.models),
        )

        try:
            response = await self.client.chat.completions.create(
                **request_options
            )
        except Exception as error:
            logger.exception(
                "Every configured OpenRouter model failed."
            )
            raise RuntimeError(
                "All OpenRouter models are currently unavailable "
                "or rate-limited."
            ) from error

        if not response.choices:
            raise RuntimeError(
                "OpenRouter returned no response choices."
            )

        message = response.choices[0].message
        content = message.content

        if not content or not content.strip():
            raise RuntimeError(
                "OpenRouter returned an empty response."
            )

        selected_model = getattr(
            response,
            "model",
            primary_model,
        )

        logger.info(
            "OpenRouter replied to user %s using %s",
            user_id,
            selected_model,
        )

        return content.strip()

    async def use_tool(
        self,
        tool: str,
        query: str,
    ):
        """
        Provider-side tools.

        "web_search" is implemented through OpenRouter's web plugin, so a free
        model behind OpenRouter can still answer current-events questions with
        real citations instead of a shrug.
        """
        if tool != "web_search":
            raise NotImplementedError(
                f"{tool} is not implemented for OpenRouter."
            )

        response = await self.client.chat.completions.create(
            model=self.models[0],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a search assistant. Answer the query using "
                        "live web results. Include the URLs you used, one per "
                        "line, prefixed with 'SOURCE:'. Do not speculate."
                    ),
                },
                {"role": "user", "content": query},
            ],
            extra_body={
                "plugins": [
                    {
                        "id": "web",
                        "max_results": int(
                            getattr(settings, "openrouter_search_results", 5)
                        ),
                    }
                ]
            },
        )

        if not response.choices:
            raise RuntimeError("OpenRouter web search returned no choices.")

        return (response.choices[0].message.content or "").strip()

    # =====================================
    # Model chain maintenance (self-healing)
    # =====================================

    def set_models(self, models: List[str]) -> List[str]:
        """Replace the runtime model chain (used by the model catalog refresh)."""
        cleaned = [model.strip() for model in models if model and model.strip()]

        if not cleaned:
            raise RuntimeError("Refusing to configure zero OpenRouter models.")

        previous = list(self.models)

        self.models = cleaned

        logger.info(
            "OpenRouter model chain updated: %s (was %s)",
            " -> ".join(cleaned),
            " -> ".join(previous),
        )

        return previous
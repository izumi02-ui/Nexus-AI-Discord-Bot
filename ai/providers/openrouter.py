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
    ) -> str:
        primary_model = self.models[0]
        fallback_models = self.models[1:]

        request_options = {
            "model": primary_model,
            "messages": conversation,
        }

        if fallback_models:
            request_options["extra_body"] = {
                "models": fallback_models,
            }

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
        raise NotImplementedError(
            f"{tool} is not implemented for OpenRouter."
        )
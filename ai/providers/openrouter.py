"""
Project Nexus

OpenRouter Provider
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
        return settings.openrouter_model

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

        return bool(
            settings.openrouter_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "OpenRouter API key missing."
            )

        logger.info(
            "Initializing OpenRouter..."
        )

        self.client = AsyncOpenAI(

            api_key=settings.openrouter_api_key,

            base_url="https://openrouter.ai/api/v1",

        )

        logger.info(
            "OpenRouter Ready."
        )

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        response = await self.client.chat.completions.create(

            model=self.model,

            messages=conversation,

        )

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return response.choices[0].message.content.strip()

    async def use_tool(
        self,
        tool: str,
        query: str,
    ):

        raise NotImplementedError(
            f"{tool} is not implemented for OpenRouter."
        )

"""
Project Nexus

OpenAI Provider
"""

from typing import Dict, List

from openai import AsyncOpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class OpenAIProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model(self) -> str:
        return settings.openai_model

    @property
    def capabilities(self):

        return ProviderCapabilities(

            vision=True,

            files=True,

            function_calling=True,

            image_generation=True,

            reasoning=True,

            streaming=True,

        )

    @property
    def available(self) -> bool:

        return bool(
            settings.openai_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "OpenAI API key missing."
            )

        logger.info(
            "Initializing OpenAI..."
        )

        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key
        )

        logger.info(
            "OpenAI Ready."
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
            f"{tool} is not implemented for OpenAI."
        )

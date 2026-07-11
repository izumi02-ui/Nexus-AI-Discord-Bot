"""
Project Nexus

DeepSeek Provider
"""

from typing import Dict, List

from openai import AsyncOpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class DeepSeekProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "DeepSeek"

    @property
    def model(self) -> str:
        return settings.deepseek_model

    @property
    def capabilities(self):

        return ProviderCapabilities(

            function_calling=True,

            reasoning=True,

            streaming=True,

        )

    @property
    def available(self) -> bool:

        return bool(
            settings.deepseek_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "DeepSeek API key missing."
            )

        logger.info(
            "Initializing DeepSeek..."
        )

        self.client = AsyncOpenAI(

            api_key=settings.deepseek_api_key,

            base_url="https://api.deepseek.com",

        )

        logger.info(
            "DeepSeek Ready."
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
            f"{tool} is not implemented for DeepSeek."
        )

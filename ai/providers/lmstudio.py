"""
Project Nexus

LM Studio Provider
"""

from typing import Dict, List

from openai import AsyncOpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class LMStudioProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "LM Studio"

    @property
    def model(self) -> str:
        return settings.lmstudio_model

    @property
    def capabilities(self):

        return ProviderCapabilities(

            vision=True,

            files=True,

            reasoning=True,

            streaming=True,

        )

    @property
    def available(self) -> bool:

        return bool(
            settings.lmstudio_url
        )

    def __init__(self):

        logger.info(
            "Initializing LM Studio..."
        )

        self.client = AsyncOpenAI(

            api_key="lmstudio",

            base_url=settings.lmstudio_url,

        )

        logger.info(
            "LM Studio Ready."
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
            f"{tool} is not implemented for LM Studio."
        )

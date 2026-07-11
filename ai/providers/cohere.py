"""
Project Nexus

Cohere Provider
"""

from typing import Dict, List

from cohere import AsyncClientV2

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class CohereProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "Cohere"

    @property
    def model(self) -> str:
        return settings.cohere_model

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
            settings.cohere_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "Cohere API key missing."
            )

        logger.info(
            "Initializing Cohere..."
        )

        self.client = AsyncClientV2(
            api_key=settings.cohere_api_key
        )

        logger.info(
            "Cohere Ready."
        )

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        response = await self.client.chat(

            model=self.model,

            messages=conversation,

        )

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return response.message.content[0].text.strip()

    async def use_tool(
        self,
        tool: str,
        query: str,
    ):

        raise NotImplementedError(
            f"{tool} is not implemented for Cohere."
        )

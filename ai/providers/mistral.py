"""
Project Nexus

Mistral Provider
"""

from typing import Dict, List

from mistralai import Mistral

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class MistralProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "Mistral"

    @property
    def model(self) -> str:
        return settings.mistral_model

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
            settings.mistral_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "Mistral API key missing."
            )

        logger.info(
            "Initializing Mistral..."
        )

        self.client = Mistral(
            api_key=settings.mistral_api_key
        )

        logger.info(
            "Mistral Ready."
        )

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        response = self.client.chat.complete_async(

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
            f"{tool} is not implemented for Mistral."
        )

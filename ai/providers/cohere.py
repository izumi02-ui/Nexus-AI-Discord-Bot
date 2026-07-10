"""
Project Nexus

Cohere Provider
"""

from typing import List, Dict

from cohere import ClientV2

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class CohereProvider(BaseProvider):

    @property
    def name(self) -> str:

        return "Cohere"

    @property
    def capabilities(self):

        return ProviderCapabilities(
            web_search=False,
            vision=False,
            files=False,
            function_calling=True,
            image_generation=False,
            code_execution=False,
        )

    def __init__(self):

        logger.info(
            "Initializing Cohere..."
        )

        self.client = ClientV2(
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

        response = self.client.chat(

            model=settings.model,

            messages=conversation,

        )

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return response.message.content[0].text.strip()

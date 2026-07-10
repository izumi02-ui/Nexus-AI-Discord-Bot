"""
Project Nexus

Mistral Provider
"""

from typing import List, Dict

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
    def capabilities(self):

        return ProviderCapabilities(
            web_search=False,
            vision=True,
            files=True,
            function_calling=True,
            image_generation=False,
            code_execution=False,
        )

    def __init__(self):

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

        response = self.client.chat.complete(

            model=settings.model,

            messages=conversation,

        )

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

"""
Project Nexus

OpenAI Provider
"""

from typing import List, Dict

from openai import OpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class OpenAIProvider(BaseProvider):

    @property
    def name(self) -> str:

        return "OpenAI"

    @property
    def capabilities(self):

        return ProviderCapabilities(
            web_search=False,
            vision=True,
            files=True,
            function_calling=True,
            image_generation=True,
            code_execution=False,
        )

    def __init__(self):

        logger.info(
            "Initializing OpenAI..."
        )

        self.client = OpenAI(
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

        response = self.client.chat.completions.create(

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

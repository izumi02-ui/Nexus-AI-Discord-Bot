"""
Project Nexus

Groq Provider
"""

from typing import List, Dict

from groq import Groq

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class GroqProvider(BaseProvider):

    @property
    def name(self) -> str:

        return "Groq"

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
            "Initializing Groq..."
        )

        self.client = Groq(
            api_key=settings.groq_api_key
        )

        logger.info(
            "Groq Ready."
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

"""
Project Nexus

DeepSeek Provider
"""

from typing import List, Dict

from openai import OpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class DeepSeekProvider(BaseProvider):

    @property
    def name(self) -> str:

        return "DeepSeek"

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
            "Initializing DeepSeek..."
        )

        self.client = OpenAI(

            api_key=settings.deepseek_api_key,

            base_url="https://api.deepseek.com"

        )

        logger.info(
            "DeepSeek Ready."
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

"""
Project Nexus

Ollama Provider
"""

from typing import Dict, List

from openai import AsyncOpenAI

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class OllamaProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def model(self) -> str:
        return settings.ollama_model

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
            settings.ollama_url
        )

    def __init__(self):

        logger.info(
            "Initializing Ollama..."
        )

        self.client = AsyncOpenAI(

            api_key="ollama",

            base_url=f"{settings.ollama_url}/v1",

        )

        logger.info(
            "Ollama Ready."
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
            f"{tool} is not implemented for Ollama."
        )

"""
Project Nexus

Gemini Provider
"""

from typing import Dict, List

from google import genai

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class GeminiProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def model(self) -> str:
        return settings.gemini_model

    @property
    def capabilities(self):

        return ProviderCapabilities(

            web_search=True,

            vision=True,

            files=True,

            function_calling=True,

            streaming=True,

            reasoning=True,

        )

    @property
    def available(self) -> bool:

        return bool(
            settings.gemini_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "Gemini API key missing."
            )

        logger.info(
            "Initializing Gemini Provider..."
        )

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

        logger.info(
            "Gemini Provider Ready."
        )

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        prompt = self._build_prompt(
            conversation
        )

        response = self.client.models.generate_content(

            model=self.model,

            contents=prompt,

        )

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return response.text.strip()

    async def use_tool(
        self,
        tool: str,
        query: str,
    ):

        raise NotImplementedError(
            f"{tool} is not implemented for Gemini."
        )

    def _build_prompt(
        self,
        conversation: List[Dict],
    ) -> str:

        return "\n\n".join(

            f"{message['role'].upper()}:\n{message['content']}"

            for message in conversation

        )

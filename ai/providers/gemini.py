"""
Project Nexus

Gemini Provider
"""

from typing import List, Dict

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
    def capabilities(self):

        return ProviderCapabilities(
            web_search=True,
            vision=True,
            files=True,
            function_calling=True,
            image_generation=False,
            code_execution=False,
        )

    def __init__(self):

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
            model=settings.model,
            contents=prompt
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
        """
        Execute a Gemini tool.

        NOTE:
        Actual implementation will be added
        in the next step.
        """

        if tool == "web_search":

            raise NotImplementedError(
                "Gemini Web Search is not implemented yet."
            )

        raise ValueError(
            f"Unknown tool: {tool}"
        )

    def _build_prompt(
        self,
        conversation: List[Dict],
    ) -> str:

        prompt = []

        for message in conversation:

            prompt.append(
                f"{message['role'].upper()}:\n{message['content']}"
            )

        return "\n\n".join(prompt)

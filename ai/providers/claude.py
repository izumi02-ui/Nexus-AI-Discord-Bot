"""
Project Nexus

Claude Provider
"""

from typing import Dict, List

from anthropic import AsyncAnthropic

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class ClaudeProvider(BaseProvider):

    @property
    def name(self) -> str:
        return "Claude"

    @property
    def model(self) -> str:
        return settings.claude_model

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
            settings.claude_api_key
        )

    def __init__(self):

        if not self.available:

            raise RuntimeError(
                "Claude API key missing."
            )

        logger.info(
            "Initializing Claude..."
        )

        self.client = AsyncAnthropic(
            api_key=settings.claude_api_key
        )

        logger.info(
            "Claude Ready."
        )

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        system = ""

        messages = []

        for message in conversation:

            if message["role"] == "system":

                system += message["content"] + "\n"

            else:

                messages.append({

                    "role": message["role"],

                    "content": message["content"],

                })

        response = await self.client.messages.create(

            model=self.model,

            max_tokens=4096,

            system=system.strip(),

            messages=messages,

        )

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return response.content[0].text.strip()

    async def use_tool(
        self,
        tool: str,
        query: str,
    ):

        raise NotImplementedError(
            f"{tool} is not implemented for Claude."
        )

"""
Project Nexus

Claude Provider
"""

from typing import List, Dict

from anthropic import Anthropic

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class ClaudeProvider(BaseProvider):

    @property
    def name(self) -> str:

        return "Claude"

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
            "Initializing Claude..."
        )

        self.client = Anthropic(
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

        response = self.client.messages.create(

            model=settings.model,

            max_tokens=4096,

            system=system.strip(),

            messages=messages,

        )

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return response.content[0].text.strip()

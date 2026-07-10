"""
Project Nexus

Ollama Provider
"""

from typing import List, Dict

import requests

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class OllamaProvider(BaseProvider):

    @property
    def name(self) -> str:

        return "Ollama"

    @property
    def capabilities(self):

        return ProviderCapabilities(
            web_search=False,
            vision=True,
            files=True,
            function_calling=False,
            image_generation=False,
            code_execution=False,
        )

    def __init__(self):

        logger.info(
            "Initializing Ollama..."
        )

        self.url = f"{settings.ollama_url}/api/chat"

        logger.info(
            "Ollama Ready."
        )

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        response = requests.post(

            self.url,

            json={

                "model": settings.model,

                "messages": conversation,

                "stream": False,

            },

            timeout=300,

        )

        response.raise_for_status()

        data = response.json()

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return data["message"]["content"].strip()

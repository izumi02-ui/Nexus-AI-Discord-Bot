"""
Project Nexus

OpenRouter Provider
"""

from typing import List, Dict

import requests

from ai.provider_capabilities import ProviderCapabilities
from ai.providers.base import BaseProvider

from utils.logger import logger
from utils.settings import settings


class OpenRouterProvider(BaseProvider):

    @property
    def name(self) -> str:

        return "OpenRouter"

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
            "Initializing OpenRouter..."
        )

        self.url = "https://openrouter.ai/api/v1/chat/completions"

        logger.info(
            "OpenRouter Ready."
        )

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        messages = []

        for message in conversation:

            messages.append({

                "role": message["role"],

                "content": message["content"],

            })

        response = requests.post(

            self.url,

            headers={

                "Authorization": f"Bearer {settings.openrouter_api_key}",

                "Content-Type": "application/json",

            },

            json={

                "model": settings.model,

                "messages": messages,

            },

            timeout=120,

        )

        response.raise_for_status()

        data = response.json()

        logger.info(
            f"{self.name} replied to {user_id}"
        )

        return data["choices"][0]["message"]["content"]

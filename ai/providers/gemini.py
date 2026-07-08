"""
Project Nexus

Gemini Provider
"""

from typing import List, Dict

from google import genai

from ai.providers.base import BaseProvider
from utils.logger import logger
from utils.settings import settings


class GeminiProvider(BaseProvider):
    """
    Google Gemini AI Provider.
    """

    @property
    def name(self) -> str:
        return "Gemini"

    def __init__(self):

        logger.info("Initializing Gemini Provider...")

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

        logger.info("Gemini Provider Ready.")

    async def ask(
        self,
        user_id: int,
        conversation: List[Dict],
    ) -> str:

        try:

            prompt = self._build_prompt(conversation)

            response = self.client.models.generate_content(
                model=settings.model,
                contents=prompt
            )

            logger.info(
                f"{self.name} replied to user {user_id}"
            )

            return response.text.strip()

        except Exception as error:

            logger.exception(
                f"{self.name} Provider Error"
            )

            raise error

    def _build_prompt(
        self,
        conversation: List[Dict],
    ) -> str:
        """
        Convert the internal conversation format
        into a Gemini prompt.
        """

        prompt = []

        for message in conversation:

            role = message["role"].upper()

            content = message["content"]

            prompt.append(
                f"{role}:\n{content}"
            )

        return "\n\n".join(prompt)

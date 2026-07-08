"""
Project Nexus

Gemini Provider
"""

from google import genai

from utils.settings import settings
from ai.providers.base import BaseProvider
from utils.logger import logger


class GeminiProvider(BaseProvider):

    def __init__(self):

        logger.info("Initializing Gemini...")

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

        logger.info("Gemini Ready.")

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ) -> str:

        try:

            prompt = ""

            for message in conversation:

                role = message["role"]

                content = message["content"]

                prompt += f"{role.upper()}:\n{content}\n\n"

            response = self.client.models.generate_content(
                model=settings.model,
                contents=prompt
            )

            return response.text

        except Exception as error:

            logger.error(error)

            raise

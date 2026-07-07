"""
Provider Manager

Responsible for choosing which AI
provider should answer.

Currently:

Gemini

Future:

Groq
OpenRouter
OpenAI
"""

from ai.providers.gemini import GeminiProvider


class ProviderManager:

    def __init__(self):

        self.provider = GeminiProvider()

    async def ask(
        self,
        user_id: int,
        message: str,
    ):

        return await self.provider.ask(
            user_id,
            message
        )

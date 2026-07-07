"""
Provider Manager
"""

from ai.providers.gemini import GeminiProvider


class ProviderManager:

    def __init__(self):

        self.provider = GeminiProvider()

    async def ask(
        self,
        user_id: int,
        conversation: list,
    ):

        return await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

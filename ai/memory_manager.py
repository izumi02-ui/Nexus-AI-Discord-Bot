"""
Memory Manager

Responsible for preparing conversations
before sending them to an AI provider.
"""

from ai.provider_manager import ProviderManager


class MemoryManager:

    def __init__(self):

        self.provider = ProviderManager()

    async def process(
        self,
        user_id: int,
        message: str,
    ) -> str:

        conversation = [
            {
                "role": "user",
                "content": message
            }
        ]

        return await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

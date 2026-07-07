"""
Project Nexus

AI Engine
"""

from ai.conversation_manager import conversation_manager
from ai.provider import ProviderManager


class AIEngine:

    def __init__(self):

        self.provider = ProviderManager()

    async def ask(
        self,
        user_id: int,
        message: str,
    ) -> str:

        conversation = await conversation_manager.build(
            user_id=user_id,
            message=message
        )

        return await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )


engine = AIEngine()

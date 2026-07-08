"""
Project Nexus

AI Engine
"""

from ai.conversation_manager import conversation_manager
from ai.provider_manager import provider_manager


class AIEngine:

    def __init__(self):

        self.provider = provider_manager

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

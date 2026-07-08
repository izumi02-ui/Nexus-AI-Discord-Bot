"""
Project Nexus

AI Engine

The central AI orchestration layer.
"""

from ai.conversation_manager import conversation_manager
from ai.provider_manager import provider_manager

from utils.logger import logger


class AIEngine:
    """
    Main AI Engine.
    """

    def __init__(self):

        self.provider = provider_manager

        logger.info("AI Engine initialized.")

    async def ask(
        self,
        user_id: int,
        message: str,
    ) -> str:
        """
        Process a user message.
        """

        logger.info(
            f"Processing request from {user_id}"
        )

        conversation = await conversation_manager.build(
            user_id=user_id,
            message=message
        )

        response = await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

        return response


engine = AIEngine()

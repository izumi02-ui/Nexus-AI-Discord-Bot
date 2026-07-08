"""
Project Nexus

AI Engine

The central AI orchestration layer.
"""

from ai.conversation_manager import conversation_manager
from ai.provider_manager import provider_manager

from database.memory import add_message

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

        # Build conversation
        conversation = await conversation_manager.build(
            user_id=user_id,
            message=message
        )

        # Ask the AI provider
        response = await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

        # Save conversation AFTER a successful reply
        add_message(
            user_id=user_id,
            role="user",
            content=message
        )

        add_message(
            user_id=user_id,
            role="assistant",
            content=response
        )

        logger.info(
            f"Conversation saved for {user_id}"
        )

        return response


engine = AIEngine()

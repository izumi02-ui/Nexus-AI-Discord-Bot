"""
Project Nexus

AI Engine

The central AI orchestration layer.
"""

from ai.conversation_manager import conversation_manager
from ai.provider_manager import provider_manager
from ai.memory_extractor import memory_extractor
from ai.request_router import request_router

from tools.manager import tool_manager

from database.memory import add_message

from utils.logger import logger
from utils.response_formatter import response_formatter


class AIEngine:
    """
    Main AI Engine.
    """

    def __init__(self):

        self.provider = provider_manager

        logger.info(
            "AI Engine initialized."
        )

    async def ask(
        self,
        user_id: int,
        message: str,
    ) -> str:

        logger.info(
            f"Processing request from {user_id}"
        )

        # =====================================
        # Route Request
        # =====================================

        route = request_router.route(
            message
        )

        # =====================================
        # Local Response
        # =====================================

        if route["type"] == "local":

            return response_formatter.format(
                request_router.local_response()
            )

        # =====================================
        # Tool Request
        # =====================================

        if route["type"] == "tool":

            result = await tool_manager.execute(
                route["tool"],
                message
            )

            if result["success"]:

                return response_formatter.format(
                    result["content"]
                )

            return response_formatter.format(
                f"⚠️ {result['error']}"
            )

        # =====================================
        # Build Conversation
        # =====================================

        conversation = await conversation_manager.build(
            user_id=user_id,
            message=message
        )

        # =====================================
        # Ask Provider
        # =====================================

        response = await self.provider.ask(
            user_id=user_id,
            conversation=conversation
        )

        # =====================================
        # Save Conversation
        # =====================================

        try:

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

        except Exception as error:

            logger.warning(
                f"Memory save failed: {error}"
            )

        # =====================================
        # Learn Facts
        # =====================================

        try:

            memory_extractor.extract(
                user_id=user_id,
                message=message,
                response=response
            )

        except Exception as error:

            logger.warning(
                f"Memory extraction failed: {error}"
            )

        # =====================================
        # Format Final Response
        # =====================================

        return response_formatter.format(
            response
        )


engine = AIEngine()

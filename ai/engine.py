"""
Project Nexus

AI Engine

The central AI orchestration layer.
"""

from ai.conversation_manager import conversation_manager
from ai.provider_manager import provider_manager
from ai.memory_extractor import memory_extractor
from ai.request_router import request_router

from search.aggregator import aggregator

from database.memory import add_message

from utils.logger import logger
from utils.response_formatter import response_formatter


class AIEngine:

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

        context = ""

        # =====================================
        # Local
        # =====================================

        if route["type"] == "local":

            return response_formatter.format(

                request_router.local_response()

            )

        # =====================================
        # Search
        # =====================================

        elif route["type"] == "search":

            try:

                results = await aggregator.search(

                    query=message,

                    tools=route["tools"],

                )

                valid = [

                    result

                    for result in results

                    if result.success

                ]

                if valid:

                    context = "\n\n".join(

                        f"[{r.source}] {r.content}"

                        for r in valid

                    )

            except Exception as error:

                logger.warning(

                    f"Search failed: {error}"

                )

        # =====================================
        # Chat
        # =====================================

        elif route["type"] == "chat":

            pass

        # =====================================
        # Build Conversation
        # =====================================

        conversation = await conversation_manager.build(

            user_id=user_id,

            message=message,

        )

        # =====================================
        # Inject Search Context
        # =====================================

        if context:

            conversation.insert(

                1,

                {

                    "role": "system",

                    "content": (

                        "The following information comes from external search results.\n"

                        "Use it if it is relevant and more up-to-date.\n\n"

                        + context

                    ),

                },

            )

        # =====================================
        # Ask Provider
        # =====================================

        response = await self.provider.ask(

            user_id=user_id,

            conversation=conversation,

        )

        # =====================================
        # Save Conversation
        # =====================================

        try:

            add_message(

                user_id=user_id,

                role="user",

                content=message,

            )

            add_message(

                user_id=user_id,

                role="assistant",

                content=response,

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

                response=response,

            )

        except Exception as error:

            logger.warning(

                f"Memory extraction failed: {error}"

            )

        return response_formatter.format(
            response
        )


engine = AIEngine()

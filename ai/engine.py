"""
Project Nexus

Central AI orchestration layer.
"""

from ai.conversation_manager import conversation_manager
from ai.memory_extractor import memory_extractor
from ai.provider_manager import provider_manager
from ai.request_router import request_router

from database.memory import add_message
from search.aggregator import aggregator
from utils.logger import logger
from utils.response_formatter import response_formatter


class AIEngine:
    def __init__(self):
        self.provider = provider_manager
        logger.info("AI Engine initialized.")

    async def ask(
        self,
        user_id: int,
        message: str,
    ) -> str:
        logger.info(
            "Processing request from %s",
            user_id,
        )

        route = request_router.route(message)

        if route["type"] == "local":
            return response_formatter.format(
                request_router.local_response(),
                user_id=user_id,
            )

        context = ""

        if route["type"] == "search":
            try:
                results = await aggregator.search(
                    query=message,
                    tools=route["tools"],
                )

                valid = [
                    result
                    for result in results
                    if getattr(result, "success", False)
                    and getattr(result, "content", "")
                    and "under development"
                    not in result.content.lower()
                ]

                context_parts = []

                for result in valid:
                    part = (
                        f"[{result.source}] "
                        f"{result.title}\n"
                        f"{result.content}"
                    )

                    if result.url:
                        part += f"\nURL: {result.url}"

                    context_parts.append(part)

                context = "\n\n".join(
                    context_parts
                )

            except Exception as error:
                logger.warning(
                    "Search failed: %s",
                    error,
                )

        conversation = await conversation_manager.build(
            user_id=user_id,
            message=message,
        )

        if context:
            conversation.insert(
                1,
                {
                    "role": "system",
                    "content": (
                        "Verified external search context follows. "
                        "Use it when relevant, do not invent details "
                        "beyond it, and cite provided URLs when useful.\n\n"
                        + context
                    ),
                },
            )

        response = await self.provider.ask(
            user_id=user_id,
            conversation=conversation,
        )

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
                "Memory save failed: %s",
                error,
            )

        try:
            memory_extractor.extract(
                user_id=user_id,
                message=message,
                response=response,
            )

        except Exception as error:
            logger.warning(
                               "Memory extraction failed: %s",
                error,
            )

        return response_formatter.format(
            response,
            user_id=user_id,
        )


engine = AIEngine()
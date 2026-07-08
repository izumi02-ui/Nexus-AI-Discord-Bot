"""
Project Nexus

Request Router

Determines whether a request
needs an AI provider.
"""

from utils.logger import logger


class RequestRouter:

    SIMPLE_GREETINGS = {

        "hi",
        "hello",
        "hey",
        "yo",
        "sup",
        "good morning",
        "good afternoon",
        "good evening",

    }

    def needs_ai(
        self,
        message: str,
    ) -> bool:

        text = message.lower().strip()

        if text in self.SIMPLE_GREETINGS:

            logger.info(
                "Greeting detected."
            )

            return False

        return True

    def local_response(
        self,
        message: str,
    ) -> str:

        return (
            "Hey! 👋 "
            "How can I help you today?"
        )


request_router = RequestRouter()

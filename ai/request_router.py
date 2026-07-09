"""
Project Nexus

Request Router

Routes user requests to either:

- Local Response
- AI
- Tool
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

    WEB_SEARCH_KEYWORDS = {

        "latest",
        "today",
        "yesterday",
        "news",
        "current",
        "currently",
        "recent",
        "update",
        "updates",
        "released",
        "release",
        "price",
        "weather",
        "score",
        "won",
        "happened",
    }

    def route(
        self,
        message: str,
    ):

        text = message.lower().strip()

        # ==========================
        # Greeting
        # ==========================

        if text in self.SIMPLE_GREETINGS:

            logger.info(
                "Greeting detected."
            )

            return {
                "type": "local"
            }

        # ==========================
        # Web Search
        # ==========================

        for keyword in self.WEB_SEARCH_KEYWORDS:

            if keyword in text:

                logger.info(
                    "Web search requested."
                )

                return {
                    "type": "tool",
                    "tool": "web_search"
                }

        # ==========================
        # AI
        # ==========================

        logger.info(
            "AI request."
        )

        return {
            "type": "ai"
        }

    def local_response(self):

        return (
            "Hey! 👋 "
            "How can I help you today?"
        )


request_router = RequestRouter()

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
        "tomorrow",
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
        "temperature",
        "forecast",
        "score",
        "match",
        "won",
        "winner",
        "results",
        "stock",
        "bitcoin",
        "crypto",
        "trending",
        "breaking",
        "live",
        "happened",
        "who is",
        "what is happening",
    }

    def route(
        self,
        message: str,
    ):

        text = message.lower().strip()

        # =====================================
        # Greeting
        # =====================================

        if text in self.SIMPLE_GREETINGS:

            logger.info(
                "Greeting detected."
            )

            return {
                "type": "local"
            }

        # =====================================
        # Web Search
        # =====================================

        if any(
            keyword in text
            for keyword in self.WEB_SEARCH_KEYWORDS
        ):

            logger.info(
                "Web Search requested."
            )

            return {
                "type": "tool",
                "tool": "web_search"
            }

        # =====================================
        # AI
        # =====================================

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

"""
Project Nexus

Smart Request Router
"""

from utils.logger import logger


class RequestRouter:

    LOCAL = {

        "hi",
        "hello",
        "hey",
        "yo",
        "sup",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",

    }

    SEARCH_KEYWORDS = {

        "latest",
        "today",
        "current",
        "news",
        "recent",
        "price",
        "buy",
        "review",
        "reviews",
        "benchmark",
        "vs",
        "compare",
        "comparison",
        "release",
        "released",
        "launch",
        "weather",
        "forecast",
        "temperature",
        "github",
        "repository",
        "repo",
        "youtube",
        "video",
        "reddit",
        "wikipedia",
        "wiki",
        "documentation",
        "docs",
        "paper",
        "research",
        "arxiv",
        "stackoverflow",
        "error",
        "exception",

    }

    TOOL_RULES = {

        "weather": [
            "weather",
            "forecast",
            "temperature",
            "rain",
            "snow",
            "humidity",
            "wind",
            "storm",
        ],

        "maps": [
            "map",
            "location",
            "where",
            "route",
            "directions",
            "near",
            "nearby",
        ],

        "currency": [
            "currency",
            "exchange",
            "convert",
            "usd",
            "eur",
            "inr",
            "gbp",
            "jpy",
        ],

        "github": [
            "github",
            "repository",
            "repo",
        ],

        "youtube": [
            "youtube",
            "video",
            "tutorial",
        ],

        "news": [
            "news",
            "latest",
            "breaking",
        ],

        "spotify": [
            "spotify",
            "song",
            "album",
            "artist",
            "playlist",
        ],

        "steam": [
            "steam",
            "game",
            "games",
        ],

        "stackoverflow": [
            "stackoverflow",
            "error",
            "exception",
            "traceback",
        ],

        "arxiv": [
            "paper",
            "research",
            "journal",
            "publication",
        ],

    }

    # =====================================

    def route(
        self,
        message: str,
    ):

        text = message.lower().strip()

        # ================================
        # Local
        # ================================

        if text in self.LOCAL:

            return {

                "type": "local"

            }

        # ================================
        # Search
        # ================================

        needs_search = any(

            keyword in text

            for keyword in self.SEARCH_KEYWORDS

        )

        if needs_search:

            tools = []

            for tool, keywords in self.TOOL_RULES.items():

                if any(

                    keyword in text

                    for keyword in keywords

                ):

                    tools.append(tool)

            tools.extend([

                "google",

                "wikipedia",

            ])

            tools = list(

                dict.fromkeys(tools)

            )

            logger.info(

                f"Search Route -> {tools}"

            )

            return {

                "type": "search",

                "tools": tools,

            }

        # ================================
        # Default Chat
        # ================================

        logger.info(

            "Chat Route"

        )

        return {

            "type": "chat"

        }

    # =====================================

    def local_response(self):

        return (

            "Hey! 👋 How can I help you today?"

        )


request_router = RequestRouter()

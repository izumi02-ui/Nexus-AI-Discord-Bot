"""
Project Nexus

Smart Request Router
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
            "where",
            "location",
            "distance",
            "directions",
            "route",
            "near",
            "nearby",
            "map",
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

        "time": [
            "time",
            "timezone",
            "clock",
        ],

        "translator": [
            "translate",
            "translation",
            "meaning",
        ],

        "github": [
            "github",
            "repository",
            "repo",
            "source code",
            "open source",
        ],

        "stackoverflow": [
            "error",
            "exception",
            "traceback",
            "bug",
        ],

        "arxiv": [
            "paper",
            "research",
            "journal",
            "publication",
            "arxiv",
        ],

        "steam": [
            "steam",
            "game",
            "games",
        ],

        "spotify": [
            "spotify",
            "song",
            "music",
            "album",
            "artist",
            "playlist",
        ],

        "youtube": [
            "youtube",
            "video",
            "watch",
            "tutorial",
        ],

        "news": [
            "news",
            "latest",
            "breaking",
            "today",
            "current",
            "recent",
        ],

    }

    def route(
        self,
        message: str,
    ):

        text = message.lower().strip()

        # =====================================
        # Local Response
        # =====================================

        if text in self.SIMPLE_GREETINGS:

            return {

                "type": "local",

            }

        # =====================================
        # Tool Selection
        # =====================================

        selected = []

        for tool, keywords in self.TOOL_RULES.items():

            if any(

                keyword in text

                for keyword in keywords

            ):

                selected.append(tool)

        # Always include these

        selected.extend([

            "google",
            "wikipedia",

        ])

        # Remove duplicates

        selected = list(

            dict.fromkeys(selected)

        )

        logger.info(

            f"Selected tools: {selected}"

        )

        # =====================================
        # Search Route
        # =====================================

        return {

            "type": "search",

            "tools": selected,

        }

    def local_response(self):

        return (

            "Hey! 👋 How can I help you today?"

        )


request_router = RequestRouter()

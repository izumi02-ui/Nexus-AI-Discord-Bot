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

        # =====================================
        # Weather
        # =====================================

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

        # =====================================
        # Maps
        # =====================================

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

        # =====================================
        # Currency
        # =====================================

        "currency": [
            "currency",
            "exchange",
            "convert",
            "usd",
            "eur",
            "inr",
            "jpy",
            "gbp",
        ],

        # =====================================
        # Time
        # =====================================

        "time": [
            "time",
            "timezone",
            "clock",
        ],

        # =====================================
        # Translator
        # =====================================

        "translator": [
            "translate",
            "translation",
            "meaning",
        ],

        # =====================================
        # GitHub
        # =====================================

        "github": [
            "github",
            "repository",
            "repo",
            "source code",
            "open source",
        ],

        # =====================================
        # Stack Overflow
        # =====================================

        "stackoverflow": [
            "error",
            "exception",
            "bug",
            "traceback",
            "stack overflow",
        ],

        # =====================================
        # arXiv
        # =====================================

        "arxiv": [
            "paper",
            "research",
            "journal",
            "publication",
            "arxiv",
        ],

        # =====================================
        # Steam
        # =====================================

        "steam": [
            "steam",
            "game",
            "games",
            "dlc",
            "achievement",
            "workshop",
        ],

        # =====================================
        # Spotify
        # =====================================

        "spotify": [
            "song",
            "music",
            "album",
            "artist",
            "playlist",
            "spotify",
        ],

        # =====================================
        # YouTube
        # =====================================

        "youtube": [
            "video",
            "youtube",
            "watch",
            "tutorial",
        ],

        # =====================================
        # News
        # =====================================

        "news": [
            "news",
            "latest",
            "today",
            "yesterday",
            "breaking",
            "current",
            "recent",
            "update",
            "updates",
        ],

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

        # Always search these

        selected.extend([

            "google",
            "wikipedia",
            "reddit",

        ])

        # Remove duplicates

        selected = list(

            dict.fromkeys(selected)

        )

        logger.info(

            f"Selected tools: {selected}"

        )

        return {

            "type": "search",

            "tools": selected,

        }

    def local_response(self):

        return (

            "Hey! 👋 "

            "How can I help you today?"

        )


request_router = RequestRouter()

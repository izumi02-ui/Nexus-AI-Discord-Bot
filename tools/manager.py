"""
Project Nexus

Tool Manager
"""

from utils.logger import logger


class ToolManager:

    def __init__(self):

        self.tools = {}

    # =====================================

    def register(
        self,
        tool,
    ):

        if tool.name in self.tools:

            logger.warning(
                f"Tool '{tool.name}' already registered."
            )

            return

        self.tools[tool.name] = tool

        logger.info(
            f"Loaded Tool: {tool.name}"
        )

    # =====================================

    def register_many(
        self,
        *tools,
    ):

        for tool in tools:

            self.register(tool)

        logger.info(
            f"{len(self.tools)} tools loaded."
        )

    # =====================================

    async def execute(
        self,
        tool_name: str,
        *args,
        **kwargs,
    ):

        tool = self.tools.get(
            tool_name
        )

        if tool is None:

            return {

                "success": False,

                "error": f"Unknown tool: {tool_name}",

            }

        try:

            return await tool.execute(
                *args,
                **kwargs,
            )

        except Exception as error:

            logger.exception(
                f"{tool_name} failed."
            )

            return {

                "success": False,

                "error": str(error),

            }

    # =====================================

    def get(
        self,
        name: str,
    ):

        return self.tools.get(name)

    # =====================================

    @property
    def available(self):

        return sorted(
            self.tools.keys()
        )


tool_manager = ToolManager()


# =====================================
# Register Tools
# =====================================

from tools.google_search import google_search
from tools.duckduckgo import duckduckgo
from tools.wikipedia import wikipedia
from tools.reddit import reddit
from tools.github import github
from tools.youtube import youtube
from tools.news import news
from tools.stackoverflow import stackoverflow
from tools.arxiv import arxiv
from tools.weather import weather
from tools.maps import maps
from tools.currency import currency
from tools.time import time_tool
from tools.translator import translator
from tools.spotify import spotify
from tools.steam import steam
from tools.ocr import ocr
from tools.vision import vision
from tools.file_reader import file_reader
from tools.web_scraper import web_scraper

tool_manager.register_many(

    google_search,
    duckduckgo,
    wikipedia,
    reddit,
    github,
    youtube,
    news,
    stackoverflow,
    arxiv,
    weather,
    maps,
    currency,
    time_tool,
    translator,
    spotify,
    steam,
    ocr,
    vision,
    file_reader,
    web_scraper,

)

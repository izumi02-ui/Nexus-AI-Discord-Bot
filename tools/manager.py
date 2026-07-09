"""
Project Nexus

Tool Manager
"""

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

from utils.logger import logger


class ToolManager:

    def __init__(self):

        self.tools = {}

        self._register(google_search)
        self._register(duckduckgo)
        self._register(wikipedia)
        self._register(reddit)
        self._register(github)
        self._register(youtube)
        self._register(news)
        self._register(stackoverflow)
        self._register(arxiv)
        self._register(weather)
        self._register(maps)
        self._register(currency)
        self._register(time_tool)
        self._register(translator)
        self._register(spotify)
        self._register(steam)
        self._register(ocr)
        self._register(vision)
        self._register(file_reader)
        self._register(web_scraper)

        logger.info(
            f"Loaded {len(self.tools)} tools."
        )

    def _register(
        self,
        tool,
    ):

        self.tools[tool.name] = tool

        logger.info(
            f"Loaded Tool: {tool.name}"
        )

    async def execute(
        self,
        tool: str,
        query: str,
    ):

        tool = self.tools.get(
            tool
        )

        if tool is None:

            raise ValueError(
                f"Unknown tool: {tool}"
            )

        return await tool.execute(
            query
        )

    def get(
        self,
        name: str,
    ):

        return self.tools.get(name)

    @property
    def available(self):

        return sorted(
            self.tools.keys()
        )


tool_manager = ToolManager()

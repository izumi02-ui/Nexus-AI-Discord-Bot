"""
Project Nexus

Weather Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class WeatherTool(BaseTool):

    @property
    def name(self) -> str:

        return "weather"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "Weather Information"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Weather Search: {query}"
        )

        # TODO:
        # OpenWeatherMap
        # WeatherAPI
        # Open-Meteo
        # Tomorrow.io

        return [

            SearchResult(

                title="Weather",

                content="Weather integration is under development.",

                source="Weather",

                confidence=1.0,

            )

        ]


weather = WeatherTool()

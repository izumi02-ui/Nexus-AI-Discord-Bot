"""
Project Nexus

Maps Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class MapsTool(BaseTool):

    @property
    def name(self) -> str:

        return "maps"

    @property
    def priority(self) -> int:

        return 99

    @property
    def description(self) -> str:

        return "Maps & Location Search"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Maps Search: {query}"
        )

        # TODO:
        # Google Maps API
        # OpenStreetMap
        # Nominatim
        # Mapbox
        # HERE Maps

        return [

            SearchResult(

                title="Maps",

                content="Maps integration is under development.",

                source="Maps",

                confidence=0.99,

            )

        ]


maps = MapsTool()

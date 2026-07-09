"""
Project Nexus

Vision Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class VisionTool(BaseTool):

    @property
    def name(self) -> str:

        return "vision"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "Image Understanding"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Vision Request: {query}"
        )

        # TODO:
        # Gemini Vision
        # GPT Vision
        # OCR Integration
        # Object Detection
        # Face Detection
        # Landmark Detection
        # Barcode / QR Detection
        # Image Captioning

        return [

            SearchResult(

                title="Vision",

                content="Vision integration is under development.",

                source="Vision",

                confidence=1.0,

            )

        ]


vision = VisionTool()

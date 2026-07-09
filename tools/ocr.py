"""
Project Nexus

OCR Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class OCRTool(BaseTool):

    @property
    def name(self) -> str:

        return "ocr"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "Optical Character Recognition"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"OCR Request: {query}"
        )

        # TODO:
        # Tesseract OCR
        # Google Vision OCR
        # PaddleOCR
        # EasyOCR
        # Azure OCR

        return [

            SearchResult(

                title="OCR",

                content="OCR integration is under development.",

                source="OCR",

                confidence=1.0,

            )

        ]


ocr = OCRTool()

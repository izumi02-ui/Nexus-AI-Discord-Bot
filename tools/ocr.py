"""
Project Nexus

OCR Tool (not implemented)

Kept as a placeholder on purpose, but it no longer pretends to work: the
previous version returned a fake "result" that ranked above real sources.

With ``implemented = False`` the aggregator skips it, health reporting shows
it as unavailable, and nobody gets a confident answer built on nothing.
"""

from typing import List

from tools.base import BaseTool


class OCRTool(BaseTool):

    keywords = ("ocr", "read image text", "extract text")

    implemented = False
    searchable = False

    @property
    def name(self) -> str:
        return "ocr"

    @property
    def description(self) -> str:
        return "Optical character recognition (needs Tesseract/Cloud OCR)"

    async def execute(self, query: str) -> List:
        raise NotImplementedError(
            "OCR is not wired up. Install pytesseract + the tesseract binary "
            "and implement OCRTool.execute, or Nexus will keep skipping it."
        )


ocr = OCRTool()

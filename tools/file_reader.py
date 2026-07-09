"""
Project Nexus

File Reader Tool
"""

from typing import List
from pathlib import Path

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class FileReaderTool(BaseTool):

    SUPPORTED_EXTENSIONS = {

        ".txt",
        ".md",
        ".pdf",
        ".docx",
        ".csv",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".ini",
        ".log",
        ".py",
        ".js",
        ".ts",
        ".java",
        ".cpp",
        ".c",
        ".cs",
        ".go",
        ".rs",
        ".html",
        ".css",

    }

    @property
    def name(self) -> str:

        return "file_reader"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "Universal File Reader"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"File Reader: {query}"
        )

        # TODO:
        # TXT
        # Markdown
        # PDF
        # DOCX
        # CSV
        # JSON
        # XML
        # YAML
        # Source Code
        # ZIP
        # Images
        # Audio
        # Video

        return [

            SearchResult(

                title="File Reader",

                content="File reader integration is under development.",

                source="File Reader",

                confidence=1.0,

            )

        ]

    def supports(
        self,
        path: str,
    ) -> bool:

        return (
            Path(path)
            .suffix
            .lower()
            in self.SUPPORTED_EXTENSIONS
        )


file_reader = FileReaderTool()

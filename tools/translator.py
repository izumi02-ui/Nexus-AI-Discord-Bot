"""
Project Nexus

Translator Tool
"""

from typing import List

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.logger import logger


class TranslatorTool(BaseTool):

    @property
    def name(self) -> str:

        return "translator"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "Language Translation"

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        logger.info(
            f"Translator: {query}"
        )

        # TODO:
        # Google Translate
        # DeepL
        # LibreTranslate

        return [

            SearchResult(

                title="Translator",

                content="Translation integration is under development.",

                source="Translator",

                confidence=1.0,

            )

        ]


translator = TranslatorTool()

"""
Project Nexus

Google Search Tool
"""

from typing import List

from google import genai
from google.genai import types

from tools.base import BaseTool
from search.search_result import SearchResult

from utils.settings import settings
from utils.logger import logger


class GoogleSearchTool(BaseTool):

    @property
    def name(self) -> str:

        return "google"

    @property
    def priority(self) -> int:

        return 100

    @property
    def description(self) -> str:

        return "Google Search"

    def __init__(self):

        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

    async def execute(
        self,
        query: str,
    ) -> List[SearchResult]:

        try:

            response = self.client.models.generate_content(
                model=settings.model,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                )
            )

            logger.info(
                f"Google Search: {query}"
            )

            return [

                SearchResult(

                    title=query,

                    content=response.text,

                    source="Google",

                    confidence=1.0,

                )

            ]

        except Exception as error:

            logger.exception(
                "Google Search Failed"
            )

            return [

                SearchResult(

                    title="Google Search Failed",

                    content=str(error),

                    source="Google",

                    confidence=0.0,

                    success=False,

                    error=str(error),

                )

            ]


google_search = GoogleSearchTool()
